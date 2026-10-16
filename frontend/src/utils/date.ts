/**
 * Parse a calendar day ("YYYY-MM-DD") as that day in local time.
 * `new Date("YYYY-MM-DD")` reads it as midnight UTC, which shows as the previous
 * day in timezones west of UTC.
 */
export function parseDay(day: string): Date {
  const [year, month, date] = day.split('-').map(Number)
  return new Date(year, month - 1, date)
}
