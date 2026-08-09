/**
 * The unit of a line, as a dropdown instead of a text field.
 *
 * Until now this was a free input field with "stuks" as the default, so whoever
 * entered 1200 litres of diesel got 1200 pieces of diesel and could look up the
 * weight themselves. A quantity without a unit means nothing.
 *
 * The list is a suggestion and not a fence. The category of the commodity
 * determines what comes first — litres and m³ for liquids, tonnes and m³ for
 * bulk, pieces and pallets for general cargo — but everything stays selectable.
 * A database of 400 commodities in 16 categories is full of exceptions, and
 * getting stuck on an exception is worse than an unusual unit.
 */
import { useTranslation } from "react-i18next";
import { UnitCatalogue } from "../api/client";

interface Props {
  value: string;
  onChange: (unit: string) => void;
  /** Category of the recognised commodity; determines which units come first. */
  category?: string | null;
  catalogue?: UnitCatalogue | null;
  id?: string;
  className?: string;
  "aria-label"?: string;
}

export default function UnitSelect({
  value,
  onChange,
  category,
  catalogue,
  id,
  className,
  ...rest
}: Props) {
  const { t } = useTranslation();

  // Without a catalogue (still loading, or offline) the field stays usable with
  // whatever is already in it. An empty dropdown is worse than no dropdown.
  if (!catalogue) {
    return (
      <input
        id={id}
        className={className}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-label={rest["aria-label"]}
      />
    );
  }

  const suggestedCodes =
    (category && catalogue.suggested_by_category[category]) || catalogue.default_suggested;
  const suggested = suggestedCodes
    .map((code) => catalogue.units.find((unit) => unit.code === code))
    .filter((unit): unit is UnitCatalogue["units"][number] => Boolean(unit));
  const rest_units = catalogue.units.filter((unit) => !suggestedCodes.includes(unit.code));

  // A value that is not in the catalogue comes from an older consignment or
  // from an import. That must not quietly disappear the moment somebody touches
  // the field, so it gets a line of its own.
  const known = catalogue.units.some((unit) => unit.code === value);

  return (
    <select
      id={id}
      className={className}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      aria-label={rest["aria-label"]}
    >
      {!known && value && <option value={value}>{value}</option>}
      <optgroup label={t("units.suggested")}>
        {suggested.map((unit) => (
          <option key={unit.code} value={unit.code}>
            {t(`units.name.${unit.code}`, unit.symbol)}
          </option>
        ))}
      </optgroup>
      <optgroup label={t("units.all")}>
        {rest_units.map((unit) => (
          <option key={unit.code} value={unit.code}>
            {t(`units.name.${unit.code}`, unit.symbol)}
          </option>
        ))}
      </optgroup>
    </select>
  );
}
