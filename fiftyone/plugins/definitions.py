"""
FiftyOne Plugin Definitions.

| Copyright 2017-2023, Voxel51, Inc.
| `voxel51.com <https://voxel51.com/>`_
|
"""
import glob
import eta.core.serial as etas

import fiftyone as fo
import os
import yaml  # BEFORE PR: add to requirements.txt
import traceback

import fiftyone.plugins.core as fopc
import fiftyone.constants as foc


# BEFORE PR: where should this go?
def find_files(root_dir, filename, extensions, max_depth):
    """Returns all files matching the given pattern, up to the given depth.

    Args:
        pattern: a glob pattern
        max_depth: the maximum depth to search

    Returns:
        a list of paths
    """
    if max_depth == 0:
        return []

    paths = []
    for i in range(1, max_depth):
        pattern_parts = [root_dir]
        pattern_parts += list("*" * i)
        pattern_parts += [filename]
        pattern = os.path.join(*pattern_parts)
        for extension in extensions:
            paths += glob.glob(pattern + "." + extension)

    return paths


MAX_PLUGIN_SEARCH_DEPTH = 3
PLUGIN_METADATA_FILENAME = "fiftyone"
PLUGIN_METADATA_EXTENSIONS = ["yml", "yaml"]
REQUIRED_PLUGIN_METADATA_KEYS = ["name"]


def find_plugin_metadata_files():
    plugins_dir = fo.config.plugins_dir

    if not plugins_dir:
        return []

    normal_locations = find_files(
        plugins_dir,
        PLUGIN_METADATA_FILENAME,
        PLUGIN_METADATA_EXTENSIONS,
        MAX_PLUGIN_SEARCH_DEPTH,
    )
    node_modules_locations = find_files(
        os.path.join(plugins_dir, "node_modules", "*"),
        PLUGIN_METADATA_FILENAME,
        PLUGIN_METADATA_EXTENSIONS,
        1,
    )
    yarn_packages_locations = find_files(
        os.path.join(plugins_dir, "packages", "*"),
        PLUGIN_METADATA_FILENAME,
        PLUGIN_METADATA_EXTENSIONS,
        1,
    )
    return normal_locations + node_modules_locations + yarn_packages_locations


class PluginDefinition:
    """A plugin definition.

    Args:
        directory: the directory containing the plugin
        metadata: a dict of plugin metadata

    Attributes:
        directory: the directory containing the plugin
        js_bundle: relative path to the JS bundle file
        js_bundle_path: absolute path to the JS bundle file
        py_entry: relative path to the Python entry file
        py_entry_path: absolute path to the Python entry file
    """

    def __init__(self, directory, metadata):
        missing = []
        if not directory:
            missing.append("directory")
        if not metadata:
            missing.append("metadata")
        if len(missing) > 0:
            raise ValueError("Missing required fields: %s" % missing)

        self.directory = directory
        self._metadata = metadata

        missing_metadata_keys = [
            k
            for k in REQUIRED_PLUGIN_METADATA_KEYS
            if not self._metadata.get(k, None)
        ]
        if len(missing_metadata_keys) > 0:
            raise ValueError(
                f"Plugin definition missing required fields: {missing_metadata_keys}"
            )

    def _get_abs_path(self, filename):
        if not filename:
            return None
        return os.path.join(self.directory, filename)

    @property
    def name(self):
        """The name of the plugin."""
        return self._metadata.get("name", None)

    @property
    def author(self):
        """The author of the plugin."""
        return self._metadata.get("author", None)

    @property
    def version(self):
        """The version of the plugin."""
        return self._metadata.get("version", None)

    @property
    def license(self):
        """The license of the plugin."""
        return self._metadata.get("license", None)

    @property
    def description(self):
        """The description of the plugin."""
        return self._metadata.get("description", None)

    @property
    def fiftyone_compatibility(self):
        """The FiftyOne compatible version as a semver string."""
        return self._metadata.get("fiftyone", {}).get("version", foc.Version)

    @property
    def operators(self):
        """The operators of the plugin."""
        return self._metadata.get("operators", [])

    @property
    def package_json_path(self):
        """The absolute path to the package.json file."""
        return self._get_abs_path("package.json")

    @property
    def has_package_json(self):
        """Whether the plugin has a package.json file."""
        return os.path.exists(self.package_json_path)

    @property
    def js_bundle(self):
        """The relative path to the JS bundle file."""
        js_bundle = self._metadata.get("js_bundle", None)
        if not js_bundle and self.has_package_json:
            pkg = etas.read_json(self.package_json_path)
            js_bundle = pkg.get("fiftyone", {}).get("script", None)
        return js_bundle or "dist/index.umd.js"

    @property
    def js_bundle_path(self):
        js_bundle = self.js_bundle
        return self._get_abs_path(js_bundle)

    @property
    def py_entry(self):
        return self._metadata.get("py_entry", "__init__.py")

    @property
    def py_entry_path(self):
        """The absolute path to the Python entry file."""
        return self._get_abs_path(self.py_entry)

    @property
    def server_path(self):
        """The default server path to the plugin."""
        return "/" + os.path.join(
            "plugins", os.path.relpath(self.directory, fo.config.plugins_dir)
        )

    @property
    def js_bundle_server_path(self):
        """The default server path to the JS bundle."""
        if self.has_js:
            return os.path.join(self.server_path, self.js_bundle)

    def can_register_operator(self, operator_name):
        """Whether the plugin can register the given operator."""
        if self.has_py and (operator_name in self.operators):
            return True
        return False

    @property
    def has_py(self):
        """Whether the plugin has a Python entry file."""
        return os.path.exists(self.py_entry_path)

    @property
    def has_js(self):
        """Whether the plugin has a JS bundle file."""
        return os.path.exists(self.js_bundle_path)

    def to_json(self):
        return {
            "name": self.name,
            "author": self.author,
            "version": self.version,
            "license": self.license,
            "description": self.description,
            "fiftyone_compatibility": self.fiftyone_compatibility,
            "operators": self.operators or [],
            "js_bundle": self.js_bundle,
            "py_entry": self.py_entry,
            "js_bundle_exists": self.has_js,
            "js_bundle_server_path": self.js_bundle_server_path,
            "has_py": self.has_py,
            "has_js": self.has_js,
            "server_path": self.server_path,
        }


def load_plugin_definition(metadata_file):
    """Loads the plugin definition from the given metadata_file."""
    try:
        with open(metadata_file, "r") as f:
            metadata_dict = yaml.safe_load(f)
            module_dir = os.path.dirname(metadata_file)
            definition = PluginDefinition(module_dir, metadata_dict)
            return definition
    except:
        traceback.print_exc()
        return None


def list_plugins():
    """
    List all PluginDefinitions for enabled plugins.
    """
    plugins = [
        pd
        for pd in [
            load_plugin_definition(
                os.path.join(p.path, PLUGIN_METADATA_FILENAME + ".yml")
            )
            for p in fopc._list_plugins(enabled_only=True)
        ]
        if pd
    ]

    return validate_plugins(plugins)


class DuplicatePluginNameError(ValueError):
    pass


class InvalidPluginDefinition(ValueError):
    pass


def validate_plugins(plugins):
    """
    Validates the given list of PluginDefinitions.
    Returns a list of valid PluginDefinitions.
    """
    results = []
    names = set()
    for plugin in plugins:
        if not plugin.name:
            raise InvalidPluginDefinition(
                "Plugin definition in %s is missing a name" % plugin.directory
            )
        if plugin.name in names:
            raise DuplicatePluginNameError(
                "Plugin name %s is not unique" % plugin.name
            )
        else:
            results.append(plugin)
        names.add(plugin.name)
    return results
