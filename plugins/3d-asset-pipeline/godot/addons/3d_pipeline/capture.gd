@tool
extends SceneTree

const REVIEW_SCENE := "res://addons/3d_pipeline/review_scene.tscn"
const SCREENSHOT_NAMES := {
	"CamFront": "front.png",
	"CamTQ": "three-quarter.png",
	"CamSide": "side.png",
	"CamBack": "back.png"
}

var _args: Dictionary = {}
var _setup: Dictionary = {}
var _root_scene: Node = null
var _slot: Node3D = null
var _asset: Node = null


func _initialize() -> void:
	DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_MINIMIZED)
	_args = _parse_args(OS.get_cmdline_user_args())

	if not _require_args(["asset", "source", "output"]):
		quit(1)
		return

	_make_dir(_args["output"])
	_setup = _read_setup(_setup_path(_args["output"]))

	var packed := load(REVIEW_SCENE)
	if packed == null:
		push_error("Unable to load review scene: %s" % REVIEW_SCENE)
		quit(1)
		return

	_root_scene = packed.instantiate()
	root.add_child(_root_scene)
	_slot = _root_scene.find_child("AssetSlot", true, false) as Node3D
	if _slot == null:
		push_error("Review scene is missing AssetSlot")
		quit(1)
		return

	if not _load_asset():
		quit(1)
		return

	await process_frame
	await process_frame
	var manifest := await _capture_all()
	_write_json(_args["output"].path_join("screenshots.json"), manifest)
	print("CAPTURED %s %s" % [_args["asset"], _args["output"]])
	quit()


func _parse_args(argv: PackedStringArray) -> Dictionary:
	var parsed := {
		"anim_frame": 0.5,
		"scale": 1.0,
		"rotation_y": 0.0
	}
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
	parsed["anim_frame"] = float(parsed.get("anim_frame", 0.5))
	parsed["scale"] = float(parsed.get("scale", 1.0))
	parsed["rotation_y"] = float(parsed.get("rotation_y", 0.0))
	return parsed


func _require_args(names: Array[String]) -> bool:
	for name in names:
		if not _args.has(name) or str(_args[name]).is_empty():
			push_error("Missing required argument --%s" % name.replace("_", "-"))
			return false
	return true


func _make_dir(path: String) -> void:
	var err := DirAccess.make_dir_recursive_absolute(path)
	if err != OK:
		push_error("Unable to create output directory: %s" % path)


func _setup_path(output_path: String) -> String:
	return output_path.get_base_dir().path_join("setup.json")


func _read_setup(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {}
	var handle := FileAccess.open(path, FileAccess.READ)
	if handle == null:
		push_warning("Unable to read setup file: %s" % path)
		return {}
	var parsed = JSON.parse_string(handle.get_as_text())
	if typeof(parsed) == TYPE_DICTIONARY:
		return parsed
	push_warning("Ignoring malformed setup file: %s" % path)
	return {}


func _load_asset() -> bool:
	var resource := load(str(_args["source"]))
	if resource == null:
		push_error("Unable to load asset: %s" % _args["source"])
		return false

	if resource is PackedScene:
		_asset = resource.instantiate()
	elif resource is Mesh:
		var mesh_instance := MeshInstance3D.new()
		mesh_instance.mesh = resource
		_asset = mesh_instance
	else:
		push_error("Unsupported asset resource type: %s" % _args["source"])
		return false

	_slot.add_child(_asset)
	_apply_setup()
	_ground_asset()
	return true


func _apply_setup() -> void:
	var final_scale := float(_setup.get("scale", _args.get("scale", 1.0)))
	var rotation_degrees := float(_setup.get("rotation_y_degrees", _args.get("rotation_y", 0.0)))
	if _asset is Node3D:
		var node := _asset as Node3D
		node.scale = Vector3.ONE * final_scale
		node.rotation_degrees.y = rotation_degrees

	var material_overrides := _setup.get("material_overrides", {})
	if typeof(material_overrides) == TYPE_DICTIONARY:
		_apply_material_overrides(_asset, material_overrides)

	var animation_name := str(_setup.get("default_animation", ""))
	if not animation_name.is_empty():
		var player := _find_animation_player(_asset)
		if player != null and player.has_animation(animation_name):
			player.play(animation_name)
			player.seek(float(_args.get("anim_frame", 0.5)), true)


func _ground_asset() -> void:
	# Generated meshes use arbitrary pivot conventions (TRELLIS.2 centers the
	# origin, so half the asset sinks below the floor). Rest the merged visual
	# AABB on the ground plane and center it horizontally so every camera sees
	# the whole asset regardless of the source pivot.
	if not (_asset is Node3D):
		return
	var node := _asset as Node3D
	var merged := _merged_aabb(_asset)
	if merged.size == Vector3.ZERO:
		return
	var center := merged.get_center()
	node.global_position -= Vector3(center.x, merged.position.y, center.z)


func _merged_aabb(node: Node) -> AABB:
	var merged := AABB()
	var found := false
	if node is VisualInstance3D:
		var visual := node as VisualInstance3D
		merged = visual.global_transform * visual.get_aabb()
		found = true
	for child in node.get_children():
		var child_aabb := _merged_aabb(child)
		if child_aabb.size == Vector3.ZERO:
			continue
		merged = merged.merge(child_aabb) if found else child_aabb
		found = true
	return merged if found else AABB()


func _apply_material_overrides(node: Node, overrides: Dictionary) -> void:
	if node is MeshInstance3D:
		var mesh_instance := node as MeshInstance3D
		for key in overrides.keys():
			var slot := _slot_index(str(key))
			if slot < 0:
				continue
			var material := _material_from_value(overrides[key])
			if material != null:
				mesh_instance.set_surface_override_material(slot, material)
	for child in node.get_children():
		_apply_material_overrides(child, overrides)


func _slot_index(value: String) -> int:
	if value.begins_with("slot_"):
		return int(value.substr(5))
	if value.is_valid_int():
		return int(value)
	return -1


func _material_from_value(value) -> Material:
	var material := StandardMaterial3D.new()
	var text := str(value)
	if text.begins_with("res://"):
		var texture := load(text)
		if texture is Texture2D:
			material.albedo_texture = texture
		else:
			material.albedo_color = Color(0.75, 0.75, 0.75)
	elif Color.html_is_valid(text):
		material.albedo_color = Color.html(text)
	else:
		material.albedo_color = Color(0.75, 0.75, 0.75)
	return material


func _capture_all() -> Dictionary:
	var images: Array = []
	for camera_name in SCREENSHOT_NAMES.keys():
		var camera := _root_scene.find_child(camera_name, true, false) as Camera3D
		if camera == null:
			push_warning("Missing camera: %s" % camera_name)
			continue
		var file_name := str(SCREENSHOT_NAMES[camera_name])
		var output_file: String = String(_args["output"]).path_join(file_name)
		await _capture_camera(camera, output_file)
		images.append({"camera": camera_name, "file": file_name, "path": output_file})

	var player := _find_animation_player(_asset)
	if player != null:
		_prepare_animation_frame(player)
		var camera := _root_scene.find_child("CamTQ", true, false) as Camera3D
		var output_file: String = String(_args["output"]).path_join("animation-mid.png")
		await _capture_camera(camera, output_file)
		images.append({"camera": "CamTQ", "file": "animation-mid.png", "path": output_file, "animation": player.current_animation})

	return {
		"asset": _args["asset"],
		"source": _args["source"],
		"output": _args["output"],
		"setup": _setup,
		"images": images
	}


func _capture_camera(camera: Camera3D, output_file: String) -> void:
	camera.make_current()
	# Force a synchronous draw with the new camera so the viewport texture
	# reflects this camera before we read it. Awaiting frame_post_draw is
	# unreliable when the host window is minimized (frames may be skipped),
	# so we explicitly drive the renderer and then await one tick to let the
	# scene tree settle before reading the texture.
	RenderingServer.force_draw(false)
	await process_frame
	var image := root.get_texture().get_image()
	var err := image.save_png(output_file)
	if err != OK:
		push_error("Failed to save screenshot: %s" % output_file)


func _find_animation_player(node: Node) -> AnimationPlayer:
	if node == null:
		return null
	if node is AnimationPlayer:
		return node as AnimationPlayer
	for child in node.get_children():
		var found := _find_animation_player(child)
		if found != null:
			return found
	return null


func _prepare_animation_frame(player: AnimationPlayer) -> void:
	var animation_name := str(_setup.get("default_animation", ""))
	if animation_name.is_empty():
		var names := player.get_animation_list()
		if names.size() > 0:
			animation_name = names[0]
	if animation_name.is_empty() or not player.has_animation(animation_name):
		return
	player.play(animation_name)
	var animation := player.get_animation(animation_name)
	var seek_time := clamp(animation.length * float(_args.get("anim_frame", 0.5)), 0.0, animation.length)
	player.seek(seek_time, true)


func _write_json(path: String, value: Dictionary) -> void:
	var handle := FileAccess.open(path, FileAccess.WRITE)
	if handle == null:
		push_error("Unable to write JSON: %s" % path)
		return
	handle.store_string(JSON.stringify(value, "\t"))
	handle.store_string("\n")
