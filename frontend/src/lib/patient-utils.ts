/**
 * Pure patient helpers shared by registration and the patient API adapter.
 */

/**
 * Calculates exact age in years, months, and days from Date of Birth.
 */
export function calculateAgeFromDob(dobString: string): {
  years: number;
  months: number;
  days: number;
} {
  const dob = new Date(dobString);
  const today = new Date();

  if (isNaN(dob.getTime()) || dob > today) {
    return { years: 0, months: 0, days: 0 };
  }

  let years = today.getFullYear() - dob.getFullYear();
  let months = today.getMonth() - dob.getMonth();
  let days = today.getDate() - dob.getDate();

  if (days < 0) {
    months -= 1;
    // Get days in previous month
    const prevMonth = new Date(today.getFullYear(), today.getMonth(), 0);
    days += prevMonth.getDate();
  }

  if (months < 0) {
    years -= 1;
    months += 12;
  }

  return {
    years: Math.max(0, years),
    months: Math.max(0, months),
    days: Math.max(0, days),
  };
}

/**
 * Calculates approximate DOB from age in years.
 */
export function calculateDobFromAge(years: number): string {
  const today = new Date();
  const birthYear = today.getFullYear() - years;
  const month = String(today.getMonth() + 1).padStart(2, "0");
  const day = String(today.getDate()).padStart(2, "0");
  return `${birthYear}-${month}-${day}`;
}
