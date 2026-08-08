/**
 * De eenheid van een regel, als keuzelijst in plaats van een tekstveld.
 *
 * Tot nu toe was dit een vrij invoerveld met "stuks" als standaard, dus wie
 * 1200 liter diesel invoerde kreeg 1200 stuks diesel en mocht het gewicht er
 * zelf bij zoeken. Een hoeveelheid zonder eenheid betekent niets.
 *
 * De lijst is een voorstel en geen hek. De categorie van het goed bepaalt wat
 * bovenaan staat — liter en m³ bij vloeistoffen, ton en m³ bij stortgoed,
 * stuks en pallet bij stukgoed — maar alles blijft kiesbaar. Een database van
 * 400 goederen in 16 categorieen zit vol uitzonderingen, en vastlopen op een
 * uitzondering is erger dan een ongebruikelijke eenheid.
 */
import { useTranslation } from "react-i18next";
import { UnitCatalogue } from "../api/client";

interface Props {
  value: string;
  onChange: (unit: string) => void;
  /** Categorie van het herkende goed; bepaalt welke eenheden bovenaan staan. */
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

  // Zonder catalogus (nog aan het laden, of offline) blijft het veld bruikbaar
  // met wat er al in staat. Een leeg dropdownmenu is erger dan geen dropdown.
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

  // Een waarde die niet in de catalogus staat komt uit een oudere zending of
  // uit een import. Die hoort niet stilletjes te verdwijnen zodra iemand het
  // veld aanraakt, dus hij krijgt zijn eigen regel.
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
