MIN_INSTRUCTOR_PER_HEAT = 3  # this is modified in roles_and_minima()
MIN_TIMING_PER_HEAT = 2
MIN_START_PER_HEAT = 1
MIN_GRID_PER_HEAT = 1


def parse_bool(value):
    """
    Safely converts a value to a boolean.

    Args:
        value (any): A truthy/falsy value (string, number, etc.).

    Returns:
        bool: True if the value is truthy, False otherwise.
    """
    return True if value else False


def sort_dict_by_value(d: dict, ascending: bool = True) -> dict:
    """
    Sorts a dictionary by its values.

    Args:
        d (dict): Dictionary to sort.
        ascending (bool): Sort direction. True for ascending, False for descending.

    Returns:
        dict: New dictionary sorted by value.
    """
    return dict(sorted(d.items(), key=lambda x: x[1], reverse=not ascending))


def sort_dict_by_nested_value(d: dict, key: str, ascending: bool = True) -> dict:
    """
    Sorts a dictionary by a specific key within each value dictionary.

    Args:
        d (dict): Dictionary to sort. Values must be dicts.
        key (str): Nested key to sort by.
        ascending (bool): Sort direction. True for ascending, False for descending.

    Returns:
        dict: New dictionary sorted by the nested key.
    """
    return dict(sorted(d.items(), key=lambda x: x[1][key], reverse=not ascending))


def sort_dict_by_nested_keys(d, keys_with_order):
    """
    Performs a multi-key sort on a dictionary of nested dictionaries.

    Args:
        d (dict): Dictionary where each value is itself a dictionary.
        keys_with_order (list[tuple[str, bool]]): List of (key, ascending) tuples.

    Returns:
        dict: New dictionary sorted by multiple nested keys.
    """
    items = list(d.items())

    for key, ascending in reversed(keys_with_order):
        items.sort(
            key=lambda item: item[1].get(
                key, float("-inf") if not ascending else float("inf")
            ),
            reverse=not ascending,
        )

    return dict(items)


def get_max_role_str_length():
    """
    Finds the length of the longest role name in the event.

    Returns:
        int: Length of the longest role name in the event.
    """
    max_length = 0
    for r in roles_and_minima("_"):
        max_length = len(r) if len(r) > max_length else max_length
    return max_length


def roles_and_minima(number_of_stations, number_of_novices=1, novice_denominator=3):
    """
    Roles and their minimum required number of individuals per heat.

    The minimum number of corner captains in a heat is equal to `number_of_stations`.

    The minimum number of instructors in a heat is equal to `number_of_novices`
    divided `novice_denominator`, or `MIN_INSTRUCTOR_PER_HEAT`, whichever is greater.

    Args:
        number_of_stations (int): Number of worker stations for the course.
        number_of_novices (int): Number of novices in the heat.
        novice_denominator (int): Ratio of novices to instructors.

    Returns:
        dict: Role names and their minimum number of individuals per heat.
    """

    return {
        "instructor": max(
            MIN_INSTRUCTOR_PER_HEAT, round(number_of_novices / novice_denominator)
        ),
        "timing": MIN_TIMING_PER_HEAT,
        "grid": MIN_GRID_PER_HEAT,
        "start": MIN_START_PER_HEAT,
        "captain": number_of_stations,
    }
