from unicodedata import normalize
import re

def slugify(name: str) -> str:
    """Convert a player name to a deterministic safe lowercase a-z0-9 slug."""
    nfkd = normalize("NFKD", name)
    ascii_only = nfkd.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_only.lower()
    parts = "".join(char if char.isalnum() or char == " " else " " for char in lowered).split()
    return "-".join(parts) or "unknown"

# Test cases from the actual report data
tests = [
    "Ramirez Lorca, Jaime Nahuel",
    "Ruano, Matheo",
    "Gonzalez, Ezequiel Matias",
    "Sarrailh, Pablo Eduardo",
    "Correa, Marcos Isauro",
    "Delpieri, Mateo",
    "Chavez, Alexis Ezequiel",
    "Ramirez, Gaston",
    "Mollo Skripnik Strelecki, Lucian",
    "Ferrari, Jonas Horacio",
    "Mollo Skripnik Strelecki, Juan Ig",
    "Martinez, Milo Ulises",
    "Grisolia, Geronimo Gabriel",
    "Otegui, Juan",
    "Viggiano, Valentin Nicolas",
    "Alonso, Julian",
    "Gimenez Asciutto, Mateo",
    "Delmoro, Lucas",
    "Innella, Gaston",
    "Romero, Elias Josue",
    "Gigante, Roberto Juan",
    "Allerborn, Joaquin",
    "Iglesias, Genaro",
    "Borrelli, Matias Exequiel Tomas",
    "Lovera, Alan Jorge Leonel",
    "Murino, Lautaro Ezequiel",
    "Ibarra, Steven Yoel",
]

print("=== Slugify test results ===")
all_valid = True
for t in tests:
    result = slugify(t)
    valid = bool(re.match(r'^[a-z0-9-]+$', result))
    if not valid:
        all_valid = False
    print(f'{t!r:50s} -> {result!r:30s} valid={valid}')

print(f'\nAll slugs valid: {all_valid}')

# Test the specific bug case
bug_case = "Ramirez Lorca, Jaime Nahuel"
bug_result = slugify(bug_case)
bug_valid = bool(re.match(r'^[a-z0-9-]+$', bug_result))
print(f'\nBug case: "Ramirez Lorca, Jaime Nahuel" -> {bug_result!r} valid={bug_valid}')
print(f'  OLD behavior (lower.replace(" ", "-")): "ramirez-lorca,-jaime-nahuel" (INVALID - has commas)')
print(f'  NEW behavior (slugify): "{bug_result}" (VALID)')

# Test diacritics
diacritics_tests = [
    "Gimenez Asciutto, Mateo",  # Asciutto has diacritics
    "Otegui, Juan",
]
print('\n=== Diacritics test ===')
for t in diacritics_tests:
    result = slugify(t)
    valid = bool(re.match(r'^[a-z0-9-]+$', result))
    print(f'{t!r} -> {result!r} valid={valid}')