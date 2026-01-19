# Async Programming with UniTask

Zero-allocation async/await for Unity using UniTask.

## Installation

### Via Package Manager

Add to `Packages/manifest.json`:

```json
{
  "dependencies": {
    "com.cysharp.unitask": "https://github.com/Cysharp/UniTask.git?path=src/UniTask/Assets/Plugins/UniTask"
  }
}
```

Or via Package Manager UI:
1. Window > Package Manager
2. Click "+" > Add package from git URL
3. Enter: `https://github.com/Cysharp/UniTask.git?path=src/UniTask/Assets/Plugins/UniTask`

## Basic Usage

### Simple Delay

```csharp
using Cysharp.Threading.Tasks;
using UnityEngine;

public class AsyncExample : MonoBehaviour
{
    private async UniTaskVoid Start()
    {
        Debug.Log("Starting...");
        await UniTask.Delay(TimeSpan.FromSeconds(2f));
        Debug.Log("2 seconds passed!");
    }
}
```

### Frame-Based Waiting

```csharp
private async UniTask WaitFrames()
{
    // Wait one frame
    await UniTask.Yield();

    // Wait until next frame
    await UniTask.NextFrame();

    // Wait specific number of frames
    await UniTask.DelayFrame(10);

    // Wait until end of frame
    await UniTask.WaitForEndOfFrame();
}
```

### Async Loading

```csharp
private async UniTask LoadSceneAsync(string sceneName)
{
    var operation = SceneManager.LoadSceneAsync(sceneName);
    await operation.ToUniTask();
    Debug.Log("Scene loaded!");
}

private async UniTask<Texture2D> LoadTextureAsync(string path)
{
    var request = Resources.LoadAsync<Texture2D>(path);
    await request.ToUniTask();
    return request.asset as Texture2D;
}
```

## Cancellation

### Using CancellationToken

```csharp
using System.Threading;

public class CancellableAsync : MonoBehaviour
{
    private CancellationTokenSource _cts;

    private async UniTaskVoid Start()
    {
        _cts = new CancellationTokenSource();

        try
        {
            await LongRunningTask(_cts.Token);
        }
        catch (OperationCanceledException)
        {
            Debug.Log("Task was cancelled");
        }
    }

    private async UniTask LongRunningTask(CancellationToken token)
    {
        for (int i = 0; i < 100; i++)
        {
            token.ThrowIfCancellationRequested();
            await UniTask.Delay(100, cancellationToken: token);
            Debug.Log($"Step {i}");
        }
    }

    public void Cancel()
    {
        _cts?.Cancel();
    }

    private void OnDestroy()
    {
        _cts?.Cancel();
        _cts?.Dispose();
    }
}
```

### Auto-Cancel on Destroy

```csharp
public class AutoCancelExample : MonoBehaviour
{
    private async UniTaskVoid Start()
    {
        // Automatically cancelled when GameObject is destroyed
        await DoSomethingAsync(this.GetCancellationTokenOnDestroy());
    }

    private async UniTask DoSomethingAsync(CancellationToken token)
    {
        await UniTask.Delay(5000, cancellationToken: token);
        Debug.Log("Completed!");
    }
}
```

## Parallel Execution

### WhenAll

```csharp
private async UniTask LoadAllAssetsAsync()
{
    var (texture, audio, prefab) = await UniTask.WhenAll(
        LoadTextureAsync("path/texture"),
        LoadAudioAsync("path/audio"),
        LoadPrefabAsync("path/prefab")
    );

    Debug.Log("All assets loaded!");
}

private async UniTask<Texture2D> LoadTextureAsync(string path) { /* ... */ }
private async UniTask<AudioClip> LoadAudioAsync(string path) { /* ... */ }
private async UniTask<GameObject> LoadPrefabAsync(string path) { /* ... */ }
```

### WhenAny

```csharp
private async UniTask RaceExample()
{
    int winnerIndex = await UniTask.WhenAny(
        Task1Async(),
        Task2Async(),
        Task3Async()
    );

    Debug.Log($"Task {winnerIndex} finished first!");
}
```

## Timeout

```csharp
private async UniTask WithTimeoutExample()
{
    var cts = new CancellationTokenSource();
    cts.CancelAfterSlim(TimeSpan.FromSeconds(5f));  // 5 second timeout

    try
    {
        await LongRunningTaskAsync(cts.Token);
    }
    catch (OperationCanceledException)
    {
        Debug.Log("Timed out!");
    }
}

// Or use TimeoutWithoutException
private async UniTask TimeoutSafeExample()
{
    bool isTimeout = await SomeTaskAsync()
        .TimeoutWithoutException(TimeSpan.FromSeconds(3f));

    if (isTimeout)
    {
        Debug.Log("Operation timed out");
    }
}
```

## Thread Switching

```csharp
private async UniTask ThreadSwitchingExample()
{
    Debug.Log($"Main thread: {Thread.CurrentThread.ManagedThreadId}");

    // Switch to thread pool
    await UniTask.SwitchToThreadPool();
    Debug.Log($"Thread pool: {Thread.CurrentThread.ManagedThreadId}");

    // Heavy computation here (not on main thread)
    var result = HeavyCalculation();

    // Switch back to main thread
    await UniTask.SwitchToMainThread();
    Debug.Log($"Main thread again: {Thread.CurrentThread.ManagedThreadId}");

    // Safe to access Unity API
    transform.position = result;
}
```

## WaitUntil / WaitWhile

```csharp
private async UniTask WaitForCondition()
{
    // Wait until condition is true
    await UniTask.WaitUntil(() => _isReady);

    // Wait while condition is true
    await UniTask.WaitWhile(() => _isLoading);

    // Wait until value changes
    await UniTask.WaitUntilValueChanged(this, x => x._currentState);
}
```

## Coroutine Interop

```csharp
private async UniTask CoroutineInterop()
{
    // Convert coroutine to UniTask
    await SomeCoroutine().ToUniTask();

    // Convert IEnumerator
    IEnumerator SomeCoroutine()
    {
        yield return new WaitForSeconds(1f);
        Debug.Log("Coroutine done");
    }
}
```

## UniTaskVoid vs UniTask

```csharp
// Use UniTaskVoid for fire-and-forget (like async void)
private async UniTaskVoid FireAndForget()
{
    await UniTask.Delay(1000);
    Debug.Log("Done");
}

// Use UniTask when you need to await or track completion
private async UniTask<int> GetValueAsync()
{
    await UniTask.Delay(1000);
    return 42;
}

// Calling
private void Start()
{
    FireAndForget().Forget();  // Explicitly ignore

    // Or
    DoSomethingAsync().Forget();
}
```

## Common Patterns

### Loading Screen

```csharp
public class LoadingScreen : MonoBehaviour
{
    [SerializeField] private Slider _progressBar;
    [SerializeField] private CanvasGroup _canvasGroup;

    public async UniTask LoadWithProgressAsync(string sceneName)
    {
        _canvasGroup.alpha = 1f;
        _canvasGroup.blocksRaycasts = true;

        var operation = SceneManager.LoadSceneAsync(sceneName);
        operation.allowSceneActivation = false;

        while (operation.progress < 0.9f)
        {
            _progressBar.value = operation.progress;
            await UniTask.Yield();
        }

        _progressBar.value = 1f;
        await UniTask.Delay(500);  // Show 100% briefly

        operation.allowSceneActivation = true;

        // Fade out
        await FadeOutAsync();
    }

    private async UniTask FadeOutAsync()
    {
        float duration = 0.5f;
        float elapsed = 0f;

        while (elapsed < duration)
        {
            elapsed += Time.deltaTime;
            _canvasGroup.alpha = 1f - (elapsed / duration);
            await UniTask.Yield();
        }

        _canvasGroup.blocksRaycasts = false;
    }
}
```

### Sequential Animation

```csharp
public async UniTask PlaySequenceAsync()
{
    await MoveToAsync(new Vector3(5, 0, 0), 1f);
    await UniTask.Delay(500);
    await RotateAsync(90f, 0.5f);
    await UniTask.Delay(500);
    await ScaleAsync(Vector3.one * 2f, 0.5f);
}

private async UniTask MoveToAsync(Vector3 target, float duration)
{
    Vector3 start = transform.position;
    float elapsed = 0f;

    while (elapsed < duration)
    {
        elapsed += Time.deltaTime;
        transform.position = Vector3.Lerp(start, target, elapsed / duration);
        await UniTask.Yield();
    }

    transform.position = target;
}
```

### Async Button Click

```csharp
using UnityEngine.UI;

public class AsyncButton : MonoBehaviour
{
    [SerializeField] private Button _button;

    private async UniTaskVoid Start()
    {
        while (true)
        {
            // Wait for button click
            await _button.OnClickAsync();

            // Disable while processing
            _button.interactable = false;

            await ProcessAsync();

            _button.interactable = true;
        }
    }

    private async UniTask ProcessAsync()
    {
        await UniTask.Delay(2000);
        Debug.Log("Processed!");
    }
}
```

## Best Practices

### Do's

- Use `CancellationToken` for long-running tasks
- Use `GetCancellationTokenOnDestroy()` for MonoBehaviour tasks
- Use `UniTaskVoid` for fire-and-forget
- Use `WhenAll` for parallel operations
- Dispose `CancellationTokenSource` when done

### Don'ts

- Don't use `async void` (use `async UniTaskVoid`)
- Don't forget to handle cancellation
- Don't call Unity API from background threads
- Don't block with `.Result` or `.Wait()`
