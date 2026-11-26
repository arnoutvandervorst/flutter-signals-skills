export function pickWinner(ids: string[]): string {
  return ids[Math.floor(Math.random() * ids.length)];
}
