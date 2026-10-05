ALPHABET = "ABCDEFGHIJKLMNOPRSTUVXYZÅÄÖ"
POINTS = dict(zip(ALPHABET, [1,3,8,1,1,3,2,3,1,7,3,2,3,1,2,4,1,1,1,4,3,8,7,8,4,4,4]))
PATTERN = [
    "T...W..d..W...T", ".d...T...T...d.", "..w...d.d...w..",
    "...T...w...T...", "W...w.d.d.w...W", ".T...T...T...T.",
    "..d.d.....d.d..", "d..w.......w..d", "..d.d.....d.d..",
    ".T...T...T...T.", "W...w.d.d.w...W", "...T...w...T...",
    "..w...d.d...w..", ".d...T...T...d.", "T...W..d..W...T",
]
def standard_bonuses():
    return [[{"T":"TL", "W":"TW", "d":"DL", "w":"DW", ".":""}[c] for c in row] for row in PATTERN]
