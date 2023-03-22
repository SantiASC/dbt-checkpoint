import argparse
import os
import time
from typing import Any, Dict, Optional, Sequence, Set, Tuple

from dbt_checkpoint.tracking import dbtCheckpointTracking
from dbt_checkpoint.utils import (
    JsonOpenError,
    add_default_args,
    get_json,
    get_missing_file_paths,
    get_model_sqls,
    get_models,
    red,
)


def has_properties_file(
    paths: Sequence[str], manifest: Dict[str, Any], discover_files: bool
) -> Tuple[int, Set[str]]:
    if discover_files:
        paths = get_missing_file_paths(paths, manifest)

    status_code = 0
    sqls = get_model_sqls(paths, manifest)
    filenames = set(sqls.keys())

    # get manifest nodes that pre-commit found as changed
    models = get_models(manifest, filenames)
    # convert to sets
    in_models = {model.filename for model in models if model.node.get("patch_path")}
    missing = filenames.difference(in_models)

    for model in missing:
        status_code = 1
        print(
            f"{red(sqls.get(model))}: "
            f"does not have model properties defined in any .yml file.",
        )
    return status_code, missing


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    add_default_args(parser)

    args = parser.parse_args(argv)

    try:
        manifest = get_json(args.manifest)
    except JsonOpenError as e:
        print(f"Unable to load manifest file ({e})")
        return 1

    start_time = time.time()
    status_code, _ = has_properties_file(
        paths=args.filenames, 
        manifest=manifest,
        discover_files=args.discover_files)
    end_time = time.time()
    script_args = vars(args)

    tracker = dbtCheckpointTracking(script_args=script_args)
    tracker.track_hook_event(
        event_name="Hook Executed",
        manifest=manifest,
        event_properties={
            "hook_name": os.path.basename(__file__),
            "description": "Check model has properties file",
            "status": status_code,
            "execution_time": end_time - start_time,
            "is_pytest": script_args.get("is_test"),
        },
    )

    return status_code


if __name__ == "__main__":
    exit(main())