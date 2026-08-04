/** Vite kan een bestand als tekst inlezen met `?raw`. TypeScript weet dat niet
 *  vanzelf; deze verklaring maakt zulke imports typecheckbaar. Gebruikt door de
 *  vertaaltests, die de bron van een component lezen in plaats van hem te
 *  renderen. */
declare module "*?raw" {
  const content: string;
  export default content;
}
