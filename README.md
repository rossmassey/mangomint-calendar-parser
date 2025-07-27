# mangomint calendar parser

This tiny utility sits on top of **exported network responses** from the Mangomint back-office web app.  Three different responses are saved locally as JSON and then fed into the parser:

1. `app-startup-check-auth.json`
2. `calendar-page-metadata.json`
3. `multi-provider-view.<month>.<day>.json` (one per day you want to parse)

Below is a quick primer on **what each file is**, **where it comes from in the browser dev-tools**, and **which pieces of the JSON the script actually touches**.

---
## 1. `app-startup-check-auth.json`
Source:
• Chrome DevTools → Network → the very first XHR called `app-startup?checkAuth=true` when the page refreshes.

Purpose for the parser:
• Provides the **master staff / provider directory** so that we can translate numerical IDs → human-readable names.

Relevant structure (all other properties are ignored):
```jsonc
{
  "auth": {
    "sharedData": {
      "selectors": {
        "staff": {
          "byId": {
            "22": { "firstName": "Sam", "lastName": null, ... },
            "12": { "firstName": "Alina", "lastName": "Tishchenko", ... },
            // … one entry per employee
          }
        }
      }
    }
  }
}
```
The parser walks the `auth.sharedData.selectors.staff.byId` object and builds a lookup table:
`staffId → "FirstName LastName"`.

---
## 2. `multi-provider-view.<month>.<day>.json`
Source:
• Chrome DevTools → Network → any XHR that matches `multi-provider-view?...` once you open the calendar and change the date.  Rename the file to include the month & day for clarity, e.g. `multi-provider-view.7.26.json`.

Purpose for the parser:
• Contains **everything that happens on a single day**—provider shifts, appointments, time-blocks, etc.

High-level shape (greatly trimmed):
```jsonc
{
  "serviceProviderIds": [17,19,18,...],
  "date": "2025-07-26",
  "shiftsByStaffIdAndDay": {
    "18": {
      "2025-07-26": [{ "startAtLocal": "10:00", "endAtLocal": "20:00", "locationId": 1 }]
    }
    // …
  },
  "appointments": {
    "byId": {
      "12429": {
        "startAtLocal": "2025-07-26T11:30:00",
        "client": { "firstName": "Gabrielle", ... },
        "appointmentParts": [
          { "serviceId": 35, "staffId": 16, "durationInMins": 60 }
        ]
      }
      // … thousands of lines trimmed
    },
    "idsByStaffId": {
      "16": [12276, 12429, 12426]
      // …
    }
  }
}
```
The parser only needs:
• `shiftsByStaffIdAndDay` → to know when a staff member is **working**.
• `appointments.byId` + `idsByStaffId` → to count **booked time** for each staff member.

Anything else (clients, payments, etc.) is ignored.

---
## 3. `calendar-page-metadata.json`
Source:
• Chrome DevTools → Network → XHR called `calendar-page-metadata?locationId=...` when you first land on the calendar.

Purpose for the parser:
• Supplies **service names & categories** so the script can show
  "HydraFacial (Service ID 115)" instead of just the numeric ID.

Relevant fragments:
```jsonc
{
  "services": {
    "servicesById": {
      "115": { "name": "HydraFacial", "defaultDuration": 60, ... },
      "138": { "name": "Blow-Dry", ... }
    },
    "serviceCategoriesById": {
      "3":   { "name": "Facials" },
      "16":  { "name": "HAIR" }
    }
  }
}
```
Only `services.servicesById` and `services.serviceCategoriesById` are accessed—the rest of the payload is left untouched.

---
### Putting it all together
When you run `python schedule_parser.py` the steps are roughly:
1. Load **all** files in memory.
2. Build the `staffId → name` map from file #1.
3. For each *multi-provider view* file (one per date):
   1. mark working hours from `shiftsByStaffIdAndDay`.
   2. subtract appointment durations via `appointments.byId`.
   3. calculate the remaining **open time** for every staff member.
4. Use file #3 to pretty-print any service IDs we encounter.

That’s it—happy scheduling! 🎉

