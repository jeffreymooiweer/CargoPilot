/** Vite can read a file as text with `?raw`. TypeScript does not know that by
 *  itself; this declaration makes such imports typecheckable. Used by the
 *  translation tests, which read the source of a component instead of rendering
 *  it. */
declare module "*?raw" {
  const content: string;
  export default content;
}
