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


class UnCardsRequest(BaseModel):
    """The declared dangerous goods, and which regimes the journey touches.

    Cards exist per UN number *and* regime; the profiles decide which
    regimes' cards belong to this shipment. Empty means every regime the
    installed set holds.
    """

    dangerous_goods: list[dict] | None = None
    profiles: list[str] = []
    output_language: str = "nl"


class DocumentExportRequest(BaseModel):
    document_key: str
    values: dict = Field(default_factory=dict)
    lines: list[dict] = Field(default_factory=list)
    dangerous_goods: list[dict] | None = None
    output_language: str = "nl"
    signature_image: str | None = None


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


class EquipmentBase(BaseModel):
    specifications: str = Field(min_length=1, max_length=255)
    length_cm: float | None = None
    width_cm: float | None = None
    height_cm: float | None = None
    #: Millimetres, as a wall is written down.
    wall_thickness_mm: float | None = None
    weight_kg: float = Field(gt=0)
    aliases: list[str] = Field(default_factory=list)
    language_labels: dict = Field(default_factory=dict)
    source: str | None = None
    notes: str | None = None
    active: bool = True


class EquipmentUpdate(BaseModel):
    specifications: str | None = Field(default=None, min_length=1, max_length=255)
    length_cm: float | None = None
    width_cm: float | None = None
    height_cm: float | None = None
    wall_thickness_mm: float | None = None
    weight_kg: float | None = Field(default=None, gt=0)
    aliases: list[str] | None = None
    language_labels: dict | None = None
    source: str | None = None
    notes: str | None = None
    active: bool | None = None


class EquipmentOut(EquipmentBase):
    id: int

    class Config:
        from_attributes = True
