def verify_metadata(data):
    if "phase.build" in data:
        data["phase.build"] = merge_build_pattern(data["phase.build"])


def merge_build_pattern(data):
    return data
