import yaml
from pathlib import Path
from typing import Any
from pipeforge.engine.pipeline import ETLPipeline
from pipeforge.models.enums import ErrorStrategy, LoadMode
from pipeforge.extractors.csv_extractor import CsvExtractor
from pipeforge.extractors.json_extractor import JsonExtractor
from pipeforge.extractors.api_extractor import ApiExtractor
from pipeforge.extractors.sql_extractor import SqlExtractor
from pipeforge.validators.schema_validator import SchemaValidator
from pipeforge.validators.rules import (
    RuleValidator,
    NotEmptyRule,
    RangeRule,
    RegexRule,
    EmailRule,
    InListRule,
)
from pipeforge.validators.quality_gate import QualityGate
from pipeforge.transformers.normalizers import (
    StringCleaner,
    CaseNormalizer,
    DateNormalizer,
    TypeCaster,
)
from pipeforge.transformers.mappers import (
    FieldRenamer,
    FieldPicker,
    FieldRemover,
    DerivedField,
    ValueMapper,
)
from pipeforge.transformers.anonymizer import FieldAnonymizer
from pipeforge.transformers.deduplicator import Deduplicator
from pipeforge.transformers.aggregator import BatchAggregator
from pipeforge.loaders.database_loader import DatabaseLoader
from pipeforge.loaders.csv_loader import CsvLoader
from pipeforge.loaders.json_loader import JsonLoader
from pipeforge.loaders.api_loader import ApiLoader


class PipelineConfigParser:
    TYPE_LOOKUP = {
        "str": str,
        "string": str,
        "int": int,
        "integer": int,
        "float": float,
        "bool": bool,
        "boolean": bool,
    }

    @classmethod
    def from_yaml_file(cls, file_path: Path | str) -> ETLPipeline:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, config: dict[str, Any]) -> ETLPipeline:
        name = config.get("name", "UnnamedPipeline")
        batch_size = config.get("batch_size", 500)
        error_strategy_str = config.get("error_strategy", "QUARANTINE").upper()
        error_strategy = ErrorStrategy(error_strategy_str)

        extractor = cls._build_extractor(config.get("source", {}))
        validators = cls._build_validators(config.get("validation", {}))
        transformers = cls._build_transformers(config.get("transformations", []))
        loaders = cls._build_loaders(config.get("destinations") or config.get("destination"))
        aggregator = cls._build_aggregator(config.get("aggregation"))
        quality_gate = cls._build_quality_gate(config.get("quality_gate"))

        return ETLPipeline(
            name=name,
            extractor=extractor,
            loaders=loaders,
            validators=validators,
            transformers=transformers,
            aggregator=aggregator,
            quality_gate=quality_gate,
            error_strategy=error_strategy,
            batch_size=batch_size,
        )

    @classmethod
    def _build_extractor(cls, src: dict[str, Any]) -> Any:
        src_type = src.get("type", "").lower()
        if src_type == "csv":
            return CsvExtractor(
                file_path=src["path"],
                delimiter=src.get("delimiter"),
                encoding=src.get("encoding", "utf-8"),
                skip_rows=src.get("skip_rows", 0),
            )
        elif src_type in ("json", "jsonl"):
            return JsonExtractor(
                file_path=src["path"],
                lines=src.get("lines", src_type == "jsonl"),
                root_key=src.get("root_key"),
                encoding=src.get("encoding", "utf-8"),
            )
        elif src_type == "api":
            return ApiExtractor(
                endpoint_url=src["url"],
                params=src.get("params"),
                headers=src.get("headers"),
                auth_token=src.get("auth_token"),
                pagination_type=src.get("pagination", "none"),
                page_size=src.get("page_size", 50),
                max_pages=src.get("max_pages", 10),
                data_key=src.get("data_key"),
            )
        elif src_type == "sql":
            return SqlExtractor(
                connection_url=src["connection_url"],
                query=src["query"],
                batch_size=src.get("batch_size", 500),
            )
        raise ValueError(f"Unknown extractor type: {src_type}")

    @classmethod
    def _build_validators(cls, val_cfg: dict[str, Any]) -> list[Any]:
        validators: list[Any] = []
        if not val_cfg:
            return validators

        if "schema" in val_cfg:
            schema_dict: dict[str, type] = {}
            for field, type_name in val_cfg["schema"].items():
                schema_dict[field] = cls.TYPE_LOOKUP.get(str(type_name).lower(), str)
            validators.append(SchemaValidator(schema_dict))

        if "rules" in val_cfg:
            rule_validator = RuleValidator()
            for rule_def in val_cfg["rules"]:
                r_type = rule_def.get("type", "").lower()
                field = rule_def["field"]
                if r_type == "not_empty":
                    rule_validator.add_rule(NotEmptyRule(field))
                elif r_type == "range":
                    rule_validator.add_rule(
                        RangeRule(
                            field_name=field,
                            min_value=rule_def.get("min"),
                            max_value=rule_def.get("max"),
                        )
                    )
                elif r_type == "regex":
                    rule_validator.add_rule(
                        RegexRule(
                            field_name=field,
                            pattern=rule_def["pattern"],
                            message=rule_def.get("message"),
                        )
                    )
                elif r_type == "email":
                    rule_validator.add_rule(EmailRule(field))
                elif r_type == "in_list":
                    rule_validator.add_rule(
                        InListRule(field_name=field, allowed_values=rule_def["allowed"])
                    )
            validators.append(rule_validator)

        return validators

    @classmethod
    def _build_transformers(cls, transforms_cfg: list[dict[str, Any]]) -> list[Any]:
        transformers: list[Any] = []
        for step in transforms_cfg:
            s_type = step.get("type", "").lower()
            if s_type == "clean_string":
                transformers.append(
                    StringCleaner(
                        fields=step.get("fields"),
                        strip_whitespace=step.get("strip", True),
                        collapse_spaces=step.get("collapse_spaces", True),
                        empty_to_none=step.get("empty_to_none", True),
                    )
                )
            elif s_type == "normalize_case":
                transformers.append(
                    CaseNormalizer(
                        fields=step["fields"],
                        mode=step.get("mode", "lower"),
                    )
                )
            elif s_type == "normalize_date":
                transformers.append(
                    DateNormalizer(
                        fields=step["fields"],
                        output_format=step.get("output_format", "%Y-%m-%d"),
                    )
                )
            elif s_type == "cast":
                type_map = {
                    k: cls.TYPE_LOOKUP.get(v.lower(), str)
                    for k, v in step["types"].items()
                }
                transformers.append(TypeCaster(type_map))
            elif s_type == "rename":
                transformers.append(FieldRenamer(step["mapping"]))
            elif s_type == "pick":
                transformers.append(FieldPicker(step["fields"]))
            elif s_type == "remove":
                transformers.append(FieldRemover(step["fields"]))
            elif s_type == "value_map":
                transformers.append(
                    ValueMapper(
                        field_name=step["field"],
                        mapping=step["mapping"],
                        default=step.get("default"),
                    )
                )
            elif s_type == "anonymize":
                transformers.append(
                    FieldAnonymizer(
                        fields=step["fields"],
                        strategy=step.get("strategy", "hash"),
                        salt=step.get("salt", ""),
                    )
                )
            elif s_type == "deduplicate":
                transformers.append(Deduplicator(key_fields=step.get("key_fields")))
            elif s_type == "derive":
                expr_str = step["expression"]
                transformers.append(
                    DerivedField(
                        field_name=step["field"],
                        expression=lambda row, expr=expr_str: eval(expr, {}, row),
                    )
                )
        return transformers

    @classmethod
    def _build_loaders(cls, dest_cfg: Any) -> list[Any]:
        if not dest_cfg:
            raise ValueError("No destination specified in configuration")

        configs = dest_cfg if isinstance(dest_cfg, list) else [dest_cfg]
        loaders: list[Any] = []

        for d in configs:
            d_type = d.get("type", "").lower()
            mode_str = d.get("mode", "APPEND").upper()
            mode = LoadMode(mode_str)

            if d_type in ("sqlite", "sql", "database"):
                loaders.append(
                    DatabaseLoader(
                        connection_url=d.get("connection_url", f"sqlite:///{d.get('path', 'output.db')}"),
                        table_name=d.get("table", "data"),
                        mode=mode,
                        primary_keys=d.get("primary_keys"),
                    )
                )
            elif d_type == "csv":
                loaders.append(
                    CsvLoader(
                        file_path=d["path"],
                        mode=mode,
                        delimiter=d.get("delimiter", ","),
                    )
                )
            elif d_type in ("json", "jsonl"):
                loaders.append(
                    JsonLoader(
                        file_path=d["path"],
                        lines=d.get("lines", d_type == "jsonl"),
                        mode=mode,
                    )
                )
            elif d_type == "api":
                loaders.append(
                    ApiLoader(
                        endpoint_url=d["url"],
                        headers=d.get("headers"),
                        auth_token=d.get("auth_token"),
                        method=d.get("method", "POST"),
                    )
                )
            else:
                raise ValueError(f"Unknown destination type: {d_type}")

        return loaders

    @classmethod
    def _build_aggregator(cls, agg_cfg: dict[str, Any] | None) -> BatchAggregator | None:
        if not agg_cfg:
            return None
        return BatchAggregator(
            group_by=agg_cfg["group_by"],
            aggregations={
                k: (v["source"], v["function"]) for k, v in agg_cfg["aggregations"].items()
            },
        )

    @classmethod
    def _build_quality_gate(cls, qg_cfg: dict[str, Any] | None) -> QualityGate | None:
        if not qg_cfg:
            return None
        return QualityGate(
            max_error_rate=qg_cfg.get("max_error_rate", 0.10),
            min_records=qg_cfg.get("min_records", 1),
            max_null_percentage=qg_cfg.get("max_null_percentage"),
            unique_fields=qg_cfg.get("unique_fields"),
        )
