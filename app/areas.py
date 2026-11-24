"""Lahore areas used when a customer has no live location (dispatch fallback centre)."""

AREAS = {
    "DHA": (31.4697, 74.4140),
    "Gulberg": (31.5204, 74.3587),
    "Johar Town": (31.4697, 74.2728),
    "Model Town": (31.4817, 74.3246),
    "Bahria Town": (31.3684, 74.1860),
    "Township": (31.4440, 74.2830),
    "Iqbal Town": (31.4959, 74.2989),
    "Wapda Town": (31.4280, 74.2660),
    "Cantt": (31.5300, 74.3700),
    "Shahdara": (31.6230, 74.2890),
}


def area_centre(name):
    return AREAS.get(name)


def area_names():
    return list(AREAS.keys())
