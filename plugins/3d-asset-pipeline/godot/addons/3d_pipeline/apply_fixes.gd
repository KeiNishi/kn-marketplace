@tool
extends SceneTree

var _args: Dictionary = {}


func _initialize() -> void:
	DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_MINIMIZED)
	_args = _parse_args(OS.get_cmdline_user_args())
	if not _args.has("fixes") or str(_args["fixes"]).is_empty():
		push_error("Missing required argument --fixes")
		quit(1)
		return
	if not _args.has("asset") or str(_args["asset"]).is_empty():
		push_error("Missing required argument --asset")
		quit(1)
		return

	var fixes := _read_json(str(_args["fixes"]))
	if fixes.is_empty():
		push_error("No fixes loaded from %s" % _args["fixes"])
		quit(1)
		return

	var setup_path := _setup_path(str(_args["fixes"]))
	var setup := _read_json(setup_path)
	_merge_setup(setup, fixes)
	_write_json(setup_path, setup)
	print("Wrote setup fixes: %s" % setup_path)

	if fixes.has("import_options") and typeof(fixes["import_options"]) == TYPE_DICTIONARY:
		_apply_import_options(str(_args["asset"]), fixes["import_options"])

	quit()


func _parse_args(argv: PackedStringArray) -> Dictionary:
	var parsed := {}
	var i := 0
	while i < argv.size():
		var key := argv[i]
		if key.begins_with("--"):
			var name := key.substr(2).replace("-", "_")
			if i + 1 < argv.size() and not argv[i + 1].begins_with("--"):
				parsed[name] = argv[i + 1]
				i += 2
			else:
				parsed[name] = true
				i += 1
		else:
			i += 1
	return parsed


func _setup_path(fixes_path: String) -> String:
	return fixes_path.get_base_dir().get_base_dir().path_join("setup.json")


func _read_json(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {}
	var handle := FileAccess.open(path, FileAccess.READ)
	if handle == null:
		return {}
	var parsed = JSON.parse_string(handle.get_as_text())
	if typeof(parsed) == TYPE_DICTIONARY:
		return parsed
	return {}


func _merge_setup(setup: Dictionary, fixes: Dictionary) -> void:
	for key in ["scale", "rotation_y_degrees", "default_animation"]:
		if fixes.has(key):
			setup[key] = fixes[key]

	for key in ["material_overrides", "import_options"]:
		if fixes.has(key) and typeof(fixes[key]) == TYPE_DICTIONARY:
			var current := {}
			if setup.has(key) and typeof(setup[key]) == TYPE_DICTIONARY:
				current = setup[key]
			for subkey in fixes[key].keys():
				current[subkey] = fixes[key][subkey]
			setup[key] = current

	if fixes.has("notes"):
		setup["notes"] = fixes["notes"]


func _write_json(path: String, value: Dictionary) -> void:
	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	var handle := FileAccess.open(path, FileAccess.WRITE)
	if handle == null:
		push_error("Unable to write JSON: %s" % path)
		return
	handle.store_string(JSON.stringify(value, "\t"))
	handle.store_string("\n")


func _apply_import_options(slug: String, options: Dictionary) -> void:
	var import_path := _find_import_file(slug)
	if import_path.is_empty():
		push_warning("No .import file found for asset %s. Import options were stored in setup.json only." % slug)
		return

	var handle := FileAccess.open(import_path, FileAccess.READ)
	if handle == null:
		push_warning("Unable to read import file: %s" % import_path)
		return
	var lines := handle.get_as_text().split("\n", false)
	var updated := _replace_params(lines, options)
	var write_handle := FileAccess.open(import_path, FileAccess.WRITE)
	if write_handle == null:
		push_warning("Unable to write import file: %s" % import_path)
		return
	write_handle.store_string("\n".join(updated))
	write_handle.store_string("\n")
	print("Updated import options in %s" % import_path)
	print("Run Godot import refresh if changed import options do not apply immediately.")


func _find_import_file(slug: String) -> String:
	var candidates := [
		"res://assets/characters/%s/%s.glb.import" % [slug, slug],
		"res://assets/characters/%s/%s.fbx.import" % [slug, slug],
		"res://assets/characters/%s/%s.tscn.import" % [slug, slug]
	]
	for candidate in candidates:
		if FileAccess.file_exists(candidate):
			return candidate
	return ""


func _replace_params(lines: PackedStringArray, options: Dictionary) -> Array[String]:
	var result: Array[String] = []
	var remaining := {}
	for key in options.keys():
		remaining[str(key)] = options[key]

	var in_params := false
	for line in lines:
		var stripped := line.strip_edges()
		if stripped.begins_with("[") and stripped.ends_with("]"):
			if in_params:
				for key in remaining.keys():
					result.append('%s=%s' % [key, _format_import_value(remaining[key])])
				remaining.clear()
			in_params = stripped == "[params]"
			result.append(line)
			continue

		if in_params:
			var eq := line.find("=")
			if eq > 0:
				var key := line.substr(0, eq)
				if remaining.has(key):
					result.append('%s=%s' % [key, _format_import_value(remaining[key])])
					remaining.erase(key)
					continue
		result.append(line)

	if in_params:
		for key in remaining.keys():
			result.append('%s=%s' % [key, _format_import_value(remaining[key])])
	elif not remaining.is_empty():
		result.append("[params]")
		for key in remaining.keys():
			result.append('%s=%s' % [key, _format_import_value(remaining[key])])
	return result


func _format_import_value(value) -> String:
	match typeof(value):
		TYPE_STRING:
			return '"%s"' % str(value)
		TYPE_BOOL:
			return "true" if bool(value) else "false"
		_:
			return str(value)
