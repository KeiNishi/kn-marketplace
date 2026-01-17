# Editor Extensions

Unityエディタ拡張実装のルールとベストプラクティス。

## 目次

1. [フォルダ構造](#フォルダ構造)
2. [CustomEditor](#customeditor)
3. [PropertyDrawer](#propertydrawer)
4. [EditorWindow](#editorwindow)
5. [ScriptableWizard](#scriptablewizard)
6. [UI Toolkit](#ui-toolkit)
7. [Menu Items](#menu-items)

---

## フォルダ構造

```
Assets/
├── Editor/                   # エディタ専用（ビルドから除外）
│   └── _Project/
│       ├── CustomEditors/    # MonoBehaviour用カスタムEditor
│       ├── PropertyDrawers/  # カスタムPropertyDrawer
│       ├── Windows/          # EditorWindow
│       ├── Wizards/          # ScriptableWizard
│       └── Utilities/        # エディタユーティリティ
```

---

## CustomEditor

### 基本構造

```csharp
using UnityEditor;
using UnityEngine;

/// <summary>
/// PlayerControllerのカスタムエディタ
/// </summary>
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
        // SerializedPropertyを取得（名前はフィールド名と一致させる）
        _moveSpeed = serializedObject.FindProperty("_moveSpeed");
        _jumpForce = serializedObject.FindProperty("_jumpForce");
        _maxHealth = serializedObject.FindProperty("_maxHealth");
    }
    
    public override void OnInspectorGUI()
    {
        // 必ず最初に呼び出す
        serializedObject.Update();
        
        // Movement セクション
        _showMovementFoldout = EditorGUILayout.Foldout(_showMovementFoldout, "Movement", true);
        if (_showMovementFoldout)
        {
            EditorGUI.indentLevel++;
            EditorGUILayout.PropertyField(_moveSpeed);
            EditorGUILayout.PropertyField(_jumpForce);
            EditorGUI.indentLevel--;
        }
        
        EditorGUILayout.Space();
        
        // Combat セクション
        _showCombatFoldout = EditorGUILayout.Foldout(_showCombatFoldout, "Combat", true);
        if (_showCombatFoldout)
        {
            EditorGUI.indentLevel++;
            EditorGUILayout.PropertyField(_maxHealth);
            EditorGUI.indentLevel--;
        }
        
        EditorGUILayout.Space();
        
        // ボタン
        if (GUILayout.Button("Reset to Defaults"))
        {
            ResetToDefaults();
        }
        
        // 必ず最後に呼び出す
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

### SceneViewでのギズモ描画

```csharp
[CustomEditor(typeof(SpawnPoint))]
public class SpawnPointEditor : Editor
{
    private void OnSceneGUI()
    {
        var spawnPoint = (SpawnPoint)target;
        var position = spawnPoint.transform.position;
        
        // ハンドル描画
        Handles.color = Color.green;
        Handles.DrawWireDisc(position, Vector3.up, spawnPoint.SpawnRadius);
        
        // 位置ハンドル（ドラッグ可能）
        EditorGUI.BeginChangeCheck();
        var newPosition = Handles.PositionHandle(position, Quaternion.identity);
        if (EditorGUI.EndChangeCheck())
        {
            Undo.RecordObject(spawnPoint.transform, "Move Spawn Point");
            spawnPoint.transform.position = newPosition;
        }
        
        // ラベル
        Handles.Label(position + Vector3.up * 2f, spawnPoint.name);
    }
}
```

---

## PropertyDrawer

### カスタムAttribute用Drawer

```csharp
// Attribute定義（通常のスクリプトフォルダ）
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

```csharp
// PropertyDrawer定義（Editorフォルダ）
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

### 使用例

```csharp
public class Enemy : MonoBehaviour
{
    [ReadOnly]
    [SerializeField] private string _uniqueId;
    
    [MinMax(0f, 100f)]
    [SerializeField] private float _health = 50f;
}
```

---

## EditorWindow

### 基本構造

```csharp
using UnityEditor;
using UnityEngine;

/// <summary>
/// ゲームデータ管理ウィンドウ
/// </summary>
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
        window.titleContent = new GUIContent("Game Data", EditorGUIUtility.IconContent("d_ScriptableObject Icon").image);
        window.minSize = new Vector2(400, 300);
    }
    
    private void OnGUI()
    {
        // ツールバー
        DrawToolbar();
        
        EditorGUILayout.Space();
        
        // タブ
        _selectedTab = GUILayout.Toolbar(_selectedTab, _tabNames);
        
        EditorGUILayout.Space();
        
        // コンテンツ（スクロール）
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
            // 検索フィールド
            _searchFilter = EditorGUILayout.TextField(
                _searchFilter, EditorStyles.toolbarSearchField, GUILayout.Width(200));
            
            GUILayout.FlexibleSpace();
            
            // ボタン
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
    
    private void DrawWeaponsTab() { /* 実装 */ }
    private void DrawCharactersTab() { /* 実装 */ }
    private void DrawItemsTab() { /* 実装 */ }
    private void RefreshData() { /* 実装 */ }
    private void CreateNewAsset() { /* 実装 */ }
}
```

---

## ScriptableWizard

### 一括処理ウィザード

```csharp
using UnityEditor;
using UnityEngine;

/// <summary>
/// プレハブ一括リネームウィザード
/// </summary>
public class RenamePrefabsWizard : ScriptableWizard
{
    [Tooltip("【用途】検索するプレフィックス")]
    public string SearchPrefix = "Old_";
    
    [Tooltip("【用途】置換後のプレフィックス")]
    public string ReplacePrefix = "New_";
    
    [Tooltip("【用途】対象フォルダ")]
    public string TargetFolder = "Assets/_Project/Prefabs";
    
    [MenuItem("Tools/Rename Prefabs Wizard")]
    public static void ShowWizard()
    {
        DisplayWizard<RenamePrefabsWizard>("Rename Prefabs", "Rename", "Preview");
    }
    
    // "Rename"ボタン押下時
    private void OnWizardCreate()
    {
        var guids = AssetDatabase.FindAssets("t:Prefab", new[] { TargetFolder });
        var count = 0;
        
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
    
    // "Preview"ボタン押下時
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
                preview.AppendLine($"  {fileName} → {newName}");
            }
        }
        
        Debug.Log(preview.ToString());
    }
    
    // バリデーション
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

---

## UI Toolkit

### Editor Window with UI Toolkit

```csharp
using UnityEditor;
using UnityEngine;
using UnityEngine.UIElements;

public class UIToolkitWindow : EditorWindow
{
    [SerializeField] private VisualTreeAsset _visualTree;
    [SerializeField] private StyleSheet _styleSheet;
    
    [MenuItem("Tools/UI Toolkit Window")]
    public static void ShowWindow()
    {
        GetWindow<UIToolkitWindow>("UI Toolkit");
    }
    
    private void CreateGUI()
    {
        // UXMLからUIを構築
        if (_visualTree != null)
        {
            _visualTree.CloneTree(rootVisualElement);
        }
        
        // スタイルシートを適用
        if (_styleSheet != null)
        {
            rootVisualElement.styleSheets.Add(_styleSheet);
        }
        
        // 要素を取得してイベント設定
        var searchField = rootVisualElement.Q<TextField>("search-field");
        searchField?.RegisterValueChangedCallback(OnSearchChanged);
        
        var refreshButton = rootVisualElement.Q<Button>("refresh-button");
        refreshButton?.clicked += OnRefreshClicked;
    }
    
    private void OnSearchChanged(ChangeEvent<string> evt)
    {
        Debug.Log($"Search: {evt.newValue}");
    }
    
    private void OnRefreshClicked()
    {
        Debug.Log("Refresh clicked");
    }
}
```

### UXML例（UIToolkitWindow.uxml）

```xml
<ui:UXML xmlns:ui="UnityEngine.UIElements">
    <ui:VisualElement class="container">
        <ui:VisualElement class="toolbar">
            <ui:TextField name="search-field" placeholder-text="Search..." />
            <ui:Button name="refresh-button" text="Refresh" />
        </ui:VisualElement>
        <ui:ScrollView name="content-area" />
    </ui:VisualElement>
</ui:UXML>
```

---

## Menu Items

### メニュー項目の追加

```csharp
using UnityEditor;
using UnityEngine;

public static class CustomMenuItems
{
    // メニューに追加
    [MenuItem("Tools/Custom/Do Something")]
    private static void DoSomething()
    {
        Debug.Log("Something done!");
    }
    
    // バリデーション（有効/無効の切り替え）
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
    
    // コンテキストメニュー（右クリック）
    [MenuItem("CONTEXT/Rigidbody/Reset Mass")]
    private static void ResetMass(MenuCommand command)
    {
        var rb = (Rigidbody)command.context;
        Undo.RecordObject(rb, "Reset Mass");
        rb.mass = 1f;
    }
    
    // ショートカット付き
    [MenuItem("Tools/Custom/Quick Action %#q")]  // Ctrl+Shift+Q
    private static void QuickAction()
    {
        Debug.Log("Quick action!");
    }
}
```

### ショートカットキー記法

| 記号 | キー |
|------|------|
| `%` | Ctrl (Windows) / Cmd (Mac) |
| `#` | Shift |
| `&` | Alt |
| `_` | 修飾キーなし（Function keyのみ） |

---

## ベストプラクティス

### Do's

- **Undo対応** - `Undo.RecordObject`で変更を記録
- **SerializedPropertyを使用** - 直接フィールドアクセスを避ける
- **EditorGUILayout使用** - 自動レイアウト
- **アイコン活用** - `EditorGUIUtility.IconContent`
- **プロパティはTooltipAttributeを活用して説明を付加する** - `[Tooltip("説明")]`
- **値範囲に制限がある場合には、RangeAttributeを使用する** - `[Range(min, max)]`

### Don'ts

- **OnGUIで重い処理をしない** - 毎フレーム呼ばれる
- **Editorフォルダ外に配置しない** - ビルドエラーになる
- **直接フィールド変更しない** - Undo/Prefabが壊れる
