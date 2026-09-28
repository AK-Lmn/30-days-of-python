import json
from pathlib import Path
import yaml
from cleanforge.models.recipe import (
    BooleanConfig,
    DateConfig,
    DuplicateConfig,
    EmailConfig,
    HeadersConfig,
    MissingConfig,
    NumberConfig,
    OutlierConfig,
    PhoneConfig,
    RecipeConfig,
    TextConfig,
    ValidationRule,
)
from cleanforge.models.types import CasingType, DuplicateKeep, ImputeStrategy, OutlierMethod, OutlierStrategy


def get_preset_recipe(preset_name: str) -> RecipeConfig:
    preset = preset_name.lower().strip()

    if preset == "customer":
        return RecipeConfig(
            name="customer_cleaning_recipe",
            version="1.0",
            headers=HeadersConfig(
                casing=CasingType.SNAKE,
                strip_whitespace=True,
                remove_special_characters=True,
                rename={
                    "email_address": "email",
                    "e_mail_address": "email",
                    "e_mail": "email",
                    "mail": "email",
                    "phone_number": "phone",
                    "telephone": "phone",
                },
            ),
            missing=MissingConfig(
                missing_values=["", "na", "n/a", "null", "none", "nan", "-", "?"],
                default_strategy=ImputeStrategy.FORWARD_FILL,
            ),
            duplicates=DuplicateConfig(
                enabled=True,
                subset=["email"],
                keep=DuplicateKeep.FIRST,
                fuzzy=True,
                similarity_threshold=0.9,
                fuzzy_columns=["first_name", "last_name"],
            ),
            text=[
                TextConfig(
                    columns=["first_name", "last_name", "city", "country"],
                    strip=True,
                    collapse_spaces=True,
                    casing=CasingType.TITLE,
                    normalize_unicode=True,
                )
            ],
            emails=[
                EmailConfig(
                    columns=["email"],
                    lowercase=True,
                    action_on_invalid="quarantine",
                )
            ],
            phones=[
                PhoneConfig(
                    columns=["phone"],
                    format="e164",
                    default_country_code="1",
                )
            ],
            dates=[
                DateConfig(
                    columns=["created_at", "signup_date", "birth_date"],
                    target_format="%Y-%m-%d",
                )
            ],
            booleans=[
                BooleanConfig(
                    columns=["is_active", "subscribed"],
                    nullable=False,
                )
            ],
            validations=[
                ValidationRule(
                    column="email",
                    not_null=True,
                    action="quarantine",
                )
            ],
        )

    if preset == "ecommerce":
        return RecipeConfig(
            name="ecommerce_cleaning_recipe",
            version="1.0",
            headers=HeadersConfig(
                casing=CasingType.SNAKE,
                strip_whitespace=True,
                remove_special_characters=True,
            ),
            missing=MissingConfig(
                default_strategy=ImputeStrategy.CONSTANT,
                default_fill_value="N/A",
            ),
            duplicates=DuplicateConfig(
                enabled=True,
                subset=["sku"],
                keep=DuplicateKeep.FIRST,
            ),
            text=[
                TextConfig(
                    columns=["title", "category"],
                    strip=True,
                    collapse_spaces=True,
                    casing=CasingType.TITLE,
                )
            ],
            numbers=[
                NumberConfig(
                    columns=["price", "cost", "discount"],
                    strip_currency=True,
                    remove_commas=True,
                    parse_percentage=True,
                    target_type="float",
                    decimals=2,
                ),
                NumberConfig(
                    columns=["stock", "quantity"],
                    target_type="int",
                    fill_on_error=0,
                ),
            ],
            booleans=[
                BooleanConfig(
                    columns=["in_stock", "is_featured"],
                )
            ],
            outliers=[
                OutlierConfig(
                    columns=["price"],
                    method=OutlierMethod.IQR,
                    strategy=OutlierStrategy.CLIP,
                    threshold=2.0,
                )
            ],
            validations=[
                ValidationRule(
                    column="price",
                    min_value=0.0,
                    action="quarantine",
                )
            ],
        )

    return RecipeConfig(
        name="standard_cleaning_recipe",
        version="1.0",
        headers=HeadersConfig(
            casing=CasingType.SNAKE,
            strip_whitespace=True,
            remove_special_characters=True,
        ),
        missing=MissingConfig(
            missing_values=["", "na", "n/a", "null", "none", "nan", "-", "?"],
        ),
        duplicates=DuplicateConfig(
            enabled=True,
            keep=DuplicateKeep.FIRST,
        ),
        text=[
            TextConfig(
                strip=True,
                collapse_spaces=True,
                normalize_unicode=True,
            )
        ],
    )


def load_recipe_file(file_path: Path | str) -> RecipeConfig:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Recipe file not found: {path}")

    content = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()

    if suffix in [".yaml", ".yml"]:
        raw_dict = yaml.safe_load(content) or {}
    else:
        raw_dict = json.loads(content)

    return RecipeConfig.model_validate(raw_dict)


def save_recipe_file(recipe: RecipeConfig, file_path: Path | str) -> None:
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()

    recipe_dict = recipe.model_dump(mode="json", exclude_none=True)

    if suffix in [".yaml", ".yml"]:
        content = yaml.safe_dump(recipe_dict, sort_keys=False)
    else:
        content = json.dumps(recipe_dict, indent=2)

    path.write_text(content, encoding="utf-8")
