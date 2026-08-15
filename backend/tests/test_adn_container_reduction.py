"""ADN 7.1.5.0.2: fewer cones for goods carried exclusively in containers.

The thresholds were read in v1.64.0 and sat in the configuration since,
recorded so they would not be read a second time when the input arrived. The
input is here now — a statement per substance that the goods travel exclusively
in containers, which is the provision's own condition and is never inferred
from a packaging type.
"""
from app.services.dg.compliance import check_adn_signals


def line(un, **extra):
    return [{"line_id": "L1", "products": [{"un_number": un, **extra}]}]


def test_without_the_statement_nothing_reduces():
    """UN 1017 chlorine shows two cones. No statement, full signals — which is
    never too few."""
    result = check_adn_signals(line("1017"))
    assert result["cones"] == 2
    assert "containers_reduction_applied" not in result


def test_class_2_below_the_threshold_shows_none():
    """Two cones, class 2, at or below 30,000 kg gross: the table says none."""
    result = check_adn_signals(line(
        "1017", containers_only="yes",
        gross_mass_per_package="500", quantity_packages="10"))
    assert result["cones"] == 0
    assert "containers_reduction_applied" in result


def test_class_2_above_the_threshold_keeps_its_cones():
    result = check_adn_signals(line(
        "1017", containers_only="yes",
        gross_mass_per_package="20000", quantity_packages="2"))
    assert result["cones"] == 2
    assert "containers_reduction_applied" not in result


def test_other_classes_show_none_at_any_mass():
    """UN 1547 aniline (6.1, PG II) carries one cone; for anything but class 2
    or packing group I the table says none, whatever the mass."""
    result = check_adn_signals(line("1547", containers_only="yes"))
    assert result["cones"] == 0
    assert "containers_reduction_applied" in result


def test_declared_without_a_mass_keeps_the_full_signals_and_says_why():
    """The threshold compares against the gross mass. Where the statement is
    made and the mass is missing, reducing anyway would understate the
    signals — the wrong direction — so the full count stands with the reason."""
    result = check_adn_signals(line("1017", containers_only="yes"))
    assert result["cones"] == 2
    assert "containers_reduction_incomplete" in result


def test_three_cones_stay_three():
    """The table's own last row: three cones reduce to nothing at all."""
    result = check_adn_signals(line("0004", containers_only="yes"))
    assert result["cones"] == 3
    assert "containers_reduction_applied" not in result
