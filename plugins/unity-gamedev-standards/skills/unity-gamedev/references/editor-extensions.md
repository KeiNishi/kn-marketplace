# Editor Extensions

Unity Editor extension implementation rules and patterns.

## Folder Structure

```
Assets/
├── Editor/                   # Editor-only (excluded from builds)
│   └── _Project/
│       ├── CustomEditors/    # MonoBehaviour custom editors
│       ├── PropertyDrawers/  # Custom property drawers
│       ├── Windows/          # EditorWindows
│       ├── Wizards/          # ScriptableWizards
│       └── Utilities/        # Editor utilities
```

## Custom Editor

### Basic Structure

```csharp
using UnityEditor;
using UnityEngine;

[CustomEditor(typeof(PlayerController))]
public class PlayerControllerEditor : Editor
{
    private SerializedProperty _moveSpeed;
    private SerializedProperty _jumpForce;
    private SerializedProperty _maxHealth;

    private bool _showMovementFoldout = true;
    private bool _showCombatFoldout = true;

    private void OnEnable()
    {
        _moveSpeed = serializedObject.FindProperty("_moveSpeed");
        _jumpForce = serializedObject.FindProperty("_jumpForce");
        _maxHealth = serializedObject.FindProperty("_maxHealth");
    }

    public override void OnInspectorGUI()
    {
        serializedObject.Update();

        // Movement section
        _showMovementFoldout = EditorGUILayout.Foldout(_showMovementFoldout, "Movement", true);
        if (_showMovementFoldout)
        {
            EditorGUI.indentLevel++;
            EditorGUILayout.PropertyField(_moveSpeed);
            EditorGUILayout.PropertyField(_jumpForce);
            EditorGUI.indentLevel--;
        }

        EditorGUILayout.Space();

        // Combat section
        _showCombatFoldout = EditorGUILayout.Foldout(_showCombatFoldout, "Combat", true);
        if (_showCombatFoldout)
        {
            EditorGUI.indentLevel++;
            EditorGUILayout.PropertyField(_maxHealth);
            EditorGUI.indentLevel--;
        }

        EditorGUILayout.Space();

        if (GUILayout.Button("Reset to Defaults"))
        {
            ResetToDefaults();
        }

        serializedObject.ApplyModifiedProperties();
    }

    private void ResetToDefaults()
    {
        Undo.RecordObject(target, "Reset Player Controller");
        _moveSpeed.floatValue = 5f;
        _jumpForce.floatValue = 10f;
        _maxHealth.intValue = 100;
    }
}
```

### Scene GUI (Gizmos)

```csharp
[CustomEditor(typeof(SpawnPoint))]
public class SpawnPointEditor : Editor
{
    private void OnSceneGUI()
    {
        var spawnPoint = (SpawnPoint)target;
        var position = spawnPoint.transform.position;

        // Draw handles
        Handles.color = Color.green;
        Handles.DrawWireDisc(position, Vector3.up, spawnPoint.SpawnRadius);

        // Position handle
        EditorGUI.BeginChangeCheck();
        var newPosition = Handles.PositionHandle(position, Quaternion.identity);
        if (EditorGUI.EndChangeCheck())
        {
            Undo.RecordObject(spawnPoint.transform, "Move Spawn Point");
            spawnPoint.transform.position = newPosition;
        }

        // Label
        Handles.Label(position + Vector3.up * 2f, spawnPoint.name);
    }
}
```

## Property Drawer

### Custom Attribute

```csharp
// Attribute definition (not in Editor folder)
using UnityEngine;

public class ReadOnlyAttribute : PropertyAttribute { }

public class MinMaxAttribute : PropertyAttribute
{
    public float Min { get; }
    public float Max { get; }

    public MinMaxAttribute(float min, float max)
    {
        Min = min;
        Max = max;
    }
}
```

### Drawer Implementation

```csharp
// In Editor folder
using UnityEditor;
using UnityEngine;

[CustomPropertyDrawer(typeof(ReadOnlyAttribute))]
public class ReadOnlyDrawer : PropertyDrawer
{
    public override void OnGUI(Rect position, SerializedProperty property, GUIContent label)
    {
        GUI.enabled = false;
        EditorGUI.PropertyField(position, property, label);
        GUI.enabled = true;
    }
}

[CustomPropertyDrawer(typeof(MinMaxAttribute))]
public class MinMaxDrawer : PropertyDrawer
{
    public override void OnGUI(Rect position, SerializedProperty property, GUIContent label)
    {
        var minMax = (MinMaxAttribute)attribute;

        if (property.propertyType == SerializedPropertyType.Float)
        {
            property.floatValue = EditorGUI.Slider(
                position, label, property.floatValue, minMax.Min, minMax.Max);
        }
        else if (property.propertyType == SerializedPropertyType.Integer)
        {
            property.intValue = EditorGUI.IntSlider(
                position, label, property.intValue, (int)minMax.Min, (int)minMax.Max);
        }
    }
}
```

### Usage

```csharp
public class Enemy : MonoBehaviour
{
    [ReadOnly]
    [SerializeField] private string _uniqueId;

    [MinMax(0f, 100f)]
    [SerializeField] private float _health = 50f;
}
```

## Editor Window

```csharp
using UnityEditor;
using UnityEngine;

public class GameDataWindow : EditorWindow
{
    private Vector2 _scrollPosition;
    private string _searchFilter = "";
    private int _selectedTab;
    private readonly string[] _tabNames = { "Weapons", "Characters", "Items" };

    [MenuItem("Tools/Game Data Manager")]
    public static void ShowWindow()
    {
        var window = GetWindow<GameDataWindow>();
        window.titleContent = new GUIContent("Game Data",
            EditorGUIUtility.IconContent("d_ScriptableObject Icon").image);
        window.minSize = new Vector2(400, 300);
    }

    private void OnGUI()
    {
        DrawToolbar();
        EditorGUILayout.Space();

        _selectedTab = GUILayout.Toolbar(_selectedTab, _tabNames);
        EditorGUILayout.Space();

        _scrollPosition = EditorGUILayout.BeginScrollView(_scrollPosition);
        {
            switch (_selectedTab)
            {
                case 0: DrawWeaponsTab(); break;
                case 1: DrawCharactersTab(); break;
                case 2: DrawItemsTab(); break;
            }
        }
        EditorGUILayout.EndScrollView();
    }

    private void DrawToolbar()
    {
        EditorGUILayout.BeginHorizontal(EditorStyles.toolbar);
        {
            _searchFilter = EditorGUILayout.TextField(
                _searchFilter, EditorStyles.toolbarSearchField, GUILayout.Width(200));

            GUILayout.FlexibleSpace();

            if (GUILayout.Button("Refresh", EditorStyles.toolbarButton))
            {
                RefreshData();
            }

            if (GUILayout.Button("Create New", EditorStyles.toolbarButton))
            {
                CreateNewAsset();
            }
        }
        EditorGUILayout.EndHorizontal();
    }

    private void DrawWeaponsTab() { }
    private void DrawCharactersTab() { }
    private void DrawItemsTab() { }
    private void RefreshData() { }
    private void CreateNewAsset() { }
}
```

## Scriptable Wizard

```csharp
using UnityEditor;
using UnityEngine;

public class RenamePrefabsWizard : ScriptableWizard
{
    [Tooltip("Prefix to search for")]
    public string SearchPrefix = "Old_";

    [Tooltip("Replacement prefix")]
    public string ReplacePrefix = "New_";

    [Tooltip("Target folder")]
    public string TargetFolder = "Assets/_Project/Prefabs";

    [MenuItem("Tools/Rename Prefabs Wizard")]
    public static void ShowWizard()
    {
        DisplayWizard<RenamePrefabsWizard>("Rename Prefabs", "Rename", "Preview");
    }

    private void OnWizardCreate()
    {
        var guids = AssetDatabase.FindAssets("t:Prefab", new[] { TargetFolder });
        int count = 0;

        foreach (var guid in guids)
        {
            var path = AssetDatabase.GUIDToAssetPath(guid);
            var fileName = System.IO.Path.GetFileNameWithoutExtension(path);

            if (fileName.StartsWith(SearchPrefix))
            {
                var newName = ReplacePrefix + fileName.Substring(SearchPrefix.Length);
                AssetDatabase.RenameAsset(path, newName);
                count++;
            }
        }

        AssetDatabase.SaveAssets();
        Debug.Log($"Renamed {count} prefabs.");
    }

    private void OnWizardOtherButton()
    {
        var guids = AssetDatabase.FindAssets("t:Prefab", new[] { TargetFolder });
        var preview = new System.Text.StringBuilder();
        preview.AppendLine("Preview of changes:");

        foreach (var guid in guids)
        {
            var path = AssetDatabase.GUIDToAssetPath(guid);
            var fileName = System.IO.Path.GetFileNameWithoutExtension(path);

            if (fileName.StartsWith(SearchPrefix))
            {
                var newName = ReplacePrefix + fileName.Substring(SearchPrefix.Length);
                preview.AppendLine($"  {fileName} -> {newName}");
            }
        }

        Debug.Log(preview.ToString());
    }

    private void OnWizardUpdate()
    {
        helpString = "Search and replace prefab name prefixes.";
        isValid = !string.IsNullOrEmpty(SearchPrefix) && !string.IsNullOrEmpty(TargetFolder);

        if (!isValid)
        {
            errorString = "Please fill in all required fields.";
        }
    }
}
```

## Menu Items

```csharp
public static class CustomMenuItems
{
    [MenuItem("Tools/Custom/Do Something")]
    private static void DoSomething()
    {
        Debug.Log("Something done!");
    }

    // With validation
    [MenuItem("Tools/Custom/Process Selected", validate = true)]
    private static bool ProcessSelectedValidate()
    {
        return Selection.activeGameObject != null;
    }

    [MenuItem("Tools/Custom/Process Selected")]
    private static void ProcessSelected()
    {
        Debug.Log($"Processing: {Selection.activeGameObject.name}");
    }

    // Context menu
    [MenuItem("CONTEXT/Rigidbody/Reset Mass")]
    private static void ResetMass(MenuCommand command)
    {
        var rb = (Rigidbody)command.context;
        Undo.RecordObject(rb, "Reset Mass");
        rb.mass = 1f;
    }

    // With shortcut (Ctrl+Shift+Q)
    [MenuItem("Tools/Custom/Quick Action %#q")]
    private static void QuickAction()
    {
        Debug.Log("Quick action!");
    }
}
```

### Shortcut Keys

| Symbol | Key |
|--------|-----|
| `%` | Ctrl (Win) / Cmd (Mac) |
| `#` | Shift |
| `&` | Alt |
| `_` | No modifier (function keys) |

## Best Practices

### Do's

- Use `Undo.RecordObject` for changes
- Use `SerializedProperty` for data access
- Use `EditorGUILayout` for auto-layout
- Use `EditorGUIUtility.IconContent` for icons
- Add `[Tooltip]` to wizard fields

### Don'ts

- Don't do heavy processing in OnGUI (called frequently)
- Don't place editor scripts outside Editor folder
- Don't modify fields directly (use SerializedProperty)
