from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(min_length=8)
    role: str = "user"


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    role: str | None = None
    active: bool | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    role: str
    active: bool

    class Config:
        from_attributes = True


class ParseRequest(BaseModel):
    text: str
    column_map: dict[str, int | None] | None = None
    has_header: bool = False
    input_language: str | None = None


class CalculateRequest(BaseModel):
    text: str | None = None
    lines: list[dict] | None = None
    column_map: dict[str, int | None] | None = None
    has_header: bool = False
    input_language: str | None = None
    output_language: str = "nl"
    mode: str = "continue"
    line_overrides: list[dict] | None = None


class ExportRequest(BaseModel):
    lines: list[dict]
    output_language: str = "nl"
    metadata: dict = Field(default_factory=dict)
    template_name: str | None = None
    dangerous_goods: list[dict] | None = None


class MaterialBase(BaseModel):
    canonical_name: str
    category: str
    density_kg_m3: float
    density_min_kg_m3: float | None = None
    density_max_kg_m3: float | None = None
    unit: str = "kg/m3"
    condition: str | None = None
    language_labels: dict = Field(default_factory=dict)
    aliases: list[str] = Field(default_factory=list)
    source: str | None = None
    notes: str | None = None
    active: bool = True


class MaterialOut(MaterialBase):
    id: int

    class Config:
        from_attributes = True


class ProfileBase(BaseModel):
    profile_type: str
    size_label: str
    kg_per_meter: float
    material: str = "steel"
    standard: str | None = None
    aliases: list[str] = Field(default_factory=list)
    source: str | None = None
    notes: str | None = None
    active: bool = True


class ProfileOut(ProfileBase):
    id: int

    class Config:
        from_attributes = True


class ReferenceItemBase(BaseModel):
    canonical_name: str
    category: str = "electrical"
    reference_weight_kg: float
    reference_volume_m3: float | None = None
    aliases: list[str] = Field(default_factory=list)
    language_labels: dict = Field(default_factory=dict)
    notes: str | None = None
    active: bool = True


class ReferenceItemOut(ReferenceItemBase):
    id: int

    class Config:
        from_attributes = True
