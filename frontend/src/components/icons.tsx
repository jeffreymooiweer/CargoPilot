/**
 * Icons shared between screens.
 *
 * Most glyphs in this application are drawn where they are used — the copy,
 * delete and pencil paths sit in the component that needs them, which keeps a
 * one-off next to its only caller. This file is for the ones that appear in
 * more than one place, so that the same action does not end up drawn twice in
 * two slightly different ways. The import glyph did exactly that: the goods
 * step and the equipment library each had their own.
 *
 * Like the notification icons, these are Uicons by Flaticon and are filled
 * rather than stroked, so `fill="currentColor"` is what makes them follow the
 * theme. No `width`/`height`: the caller decides the size.
 */

interface IconProps {
  className?: string;
}

/** Importing a spreadsheet: a document with an arrow going into it. */
export function ImportIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="m19.949,5.536l-3.484-3.486c-1.323-1.322-3.081-2.05-4.95-2.05h-4.515C4.243,0,2,2.243,2,5v6c0,.552.447,1,1,1s1-.448,1-1v-6c0-1.654,1.346-3,3-3h4.515c.163,0,.325.008.485.023v4.977c0,1.654,1.346,3,3,3h4.977c.015.16.023.322.023.485v8.515c0,1.654-1.346,3-3,3H7c-1.654,0-3-1.346-3-3,0-.552-.447-1-1-1s-1,.448-1,1c0,2.757,2.243,5,5,5h10c2.757,0,5-2.243,5-5v-8.515c0-1.871-.729-3.628-2.051-4.95Zm-4.949,2.464c-.552,0-1-.449-1-1V2.659c.38.218.733.487,1.051.805l3.484,3.486c.318.317.587.67.805,1.05h-4.341Zm-4.602,8H1c-.553,0-1-.448-1-1s.447-1,1-1h9.398l-1.293-1.293c-.391-.391-.391-1.024,0-1.414.391-.391,1.023-.391,1.414,0l1.613,1.614c1.154,1.154,1.154,3.032,0,4.187l-1.613,1.614c-.195.195-.451.293-.707.293s-.512-.098-.707-.293c-.391-.39-.391-1.023,0-1.414l1.293-1.293Z" />
    </svg>
  );
}
