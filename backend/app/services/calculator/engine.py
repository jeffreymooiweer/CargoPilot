import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class LineStatus(str, Enum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    NEEDS_REVIEW = "needs_review"


STEEL_DENSITY = 7850.0


@dataclass
class CalculationResult:
    weight_each_kg: float | None = None
    weight_total_kg: float | None = None
    material_volume_m3: float | None = None
    transport_volume_m3: float | None = None
    transport_length_m: float | None = None
    transport_width_m: float | None = None
    transport_height_m: float | None = None
    method: str | None = None
    status: LineStatus = LineStatus.OK
    messages: list[str] = field(default_factory=list)
    confidence: float = 1.0


def calc_solid_block(length_m: float, width_m: float, height_m: float, density: float) -> tuple[float, float]:
    vol = length_m * width_m * height_m
    return vol, vol * density


def calc_round_bar(radius_m: float, length_m: float, density: float) -> tuple[float, float]:
    area = math.pi * radius_m**2
    vol = area * length_m
    return vol, vol * density


def calc_round_tube(outer_r: float, inner_r: float, length_m: float, density: float) -> tuple[float, float]:
    area = math.pi * (outer_r**2 - inner_r**2)
    vol = area * length_m
    return vol, vol * density


def calc_hollow_rect(outer_w: float, outer_h: float, wall: float, length_m: float, density: float) -> tuple[float, float]:
    inner_w = outer_w - 2 * wall
    inner_h = outer_h - 2 * wall
    if inner_w <= 0 or inner_h <= 0:
        raise ValueError("Wall thickness too large for outer dimensions")
    outer_area = outer_w * outer_h
    inner_area = inner_w * inner_h
    area = outer_area - inner_area
    vol = area * length_m
    return vol, vol * density


def calc_angle_profile(leg_a: float, leg_b: float, thickness: float, length_m: float, density: float) -> tuple[float, float]:
    area = leg_a * thickness + leg_b * thickness - thickness**2
    vol = area * length_m
    return vol, vol * density


def calc_catalog_profile(kg_per_meter: float, length_m: float, quantity: float) -> tuple[float, float]:
    weight_each = kg_per_meter * length_m
    return 0.0, weight_each * quantity


def transport_volume_outer(outer_w: float, outer_h: float, length_m: float, quantity: float) -> float:
    return outer_w * outer_h * length_m * quantity
