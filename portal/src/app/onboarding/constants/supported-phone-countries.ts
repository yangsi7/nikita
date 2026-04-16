/**
 * ElevenLabs / Twilio supported phone-country codes for the voice-onboarding path.
 *
 * Spec 214 NR-3: the wizard's phone-step must reject dial codes not in this
 * list client-side and auto-route the user to the Telegram path with the
 * Nikita-voiced message "I can't reach you there. Let's use Telegram."
 *
 * ISO-3166-1 alpha-2 codes; libphonenumber-js parses a full E.164 number to
 * one of these and we check membership.
 *
 * Source: Twilio voice-supported list + ElevenLabs agent configuration
 * (coverage is a subset of Twilio's; pruned to markets Nikita's agent is
 * permissioned for). Update alongside the ElevenLabs dashboard when new
 * regions are enabled.
 *
 * Last reviewed: 2026-04-16 (Spec 214).
 */

export const SUPPORTED_PHONE_COUNTRIES: readonly string[] = [
  // North America
  "US",
  "CA",
  "MX",
  // Europe (EEA + UK + Switzerland)
  "GB",
  "IE",
  "FR",
  "DE",
  "CH",
  "AT",
  "NL",
  "BE",
  "LU",
  "ES",
  "PT",
  "IT",
  "DK",
  "SE",
  "NO",
  "FI",
  "IS",
  "PL",
  "CZ",
  "SK",
  "HU",
  "GR",
  "RO",
  "BG",
  "HR",
  "SI",
  "EE",
  "LV",
  "LT",
  // Oceania
  "AU",
  "NZ",
  // Asia-Pacific (select)
  "JP",
  "KR",
  "SG",
  "HK",
  "TW",
  // Middle East / Latin America (select)
  "IL",
  "AE",
  "BR",
  "AR",
  "CL",
] as const

/**
 * Returns true if `country` (ISO-3166-1 alpha-2) is in the supported list.
 * Case-insensitive.
 */
export function isSupportedPhoneCountry(country: string | null | undefined): boolean {
  if (!country) return false
  return SUPPORTED_PHONE_COUNTRIES.includes(country.toUpperCase())
}
