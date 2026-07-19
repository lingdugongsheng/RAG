export const API = {
  chatStream(query, { onToken, onDone, onError, onRetry }) {
    let controller = new AbortController();
    let signal = controller.signal;
    let retryCount = 0;
    const MAX_RETRIES = 1;
    let timeoutId;

    const start = () => {
      (async () => {
        try {
          const resp = await fetch('/chat/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query }),
            signal,
          });
          if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
          const reader = resp.body.getReader();
          const decoder = new TextDecoder();
          let buffer = '';

          const resetTimeout = () => {
            if (timeoutId) clearTimeout(timeoutId);
            timeoutId = setTimeout(() => {
              controller.abort();
              if (retryCount < MAX_RETRIES) {
                retryCount++;
                onRetry && onRetry();
                controller = new AbortController();
                signal = controller.signal;
                start();
              } else {
                onError && onError(new Error('响应超时，请重试'));
              }
            }, 15000); // 15秒无数据则超时
          };

          resetTimeout();

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const frames = buffer.split('\n\n');
            buffer = frames.pop() || '';
            for (const frame of frames) {
              const lines = frame.split('\n');
              for (const line of lines) {
                if (line.startsWith('data: ')) {
                  const data = line.slice(6).trim();
                  if (data === '[DONE]') {
                    if (timeoutId) clearTimeout(timeoutId);
                    onDone && onDone();
                    return;
                  }
                  try {
                    const parsed = JSON.parse(data);
                    if (parsed.token) onToken(parsed.token);
                    resetTimeout();
                  } catch (e) {}
                }
              }
            }
          }
        } catch (err) {
          if (timeoutId) clearTimeout(timeoutId);
          if (err.name === 'AbortError') {
            // 如果是主动中止则不报错
            if (!retryCount) onDone && onDone();
            return;
          }
          if (retryCount < MAX_RETRIES) {
            retryCount++;
            onRetry && onRetry();
            controller = new AbortController();
            signal = controller.signal;
            start();
          } else {
            onError && onError(err);
          }
        }
      })();
    };

    start();
    return () => {
      if (timeoutId) clearTimeout(timeoutId);
      controller.abort();
    };
  },

  async chat(query, history = []) {
    const resp = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, history }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return await resp.json();
  },

  uploadFile(file, { onStatus, onProgress }) {
    const controller = new AbortController();
    const signal = controller.signal;

    // 使用 XMLHttpRequest 以获取上传进度
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/upload');
    xhr.responseType = 'json';

    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable && onProgress) {
        const percent = Math.round((e.loaded / e.total) * 100);
        onProgress(percent);
      }
    });

    xhr.addEventListener('load', async () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        const data = xhr.response;
        if (data && data.task_id) {
          const taskId = data.task_id;
          const maxAttempts = 30;
          const timeout = 30000;
          const startTime = Date.now();
          let attempts = 0;
          // 模拟进度到90%
          let fakeProgress = onProgress ? 90 : 0;
          const progressInterval = setInterval(() => {
            if (fakeProgress < 90) {
              fakeProgress = Math.min(90, fakeProgress + 5);
              onProgress && onProgress(fakeProgress);
            }
          }, 500);

          while (attempts < maxAttempts) {
            if (Date.now() - startTime > timeout) {
              clearInterval(progressInterval);
              onStatus && onStatus({ status: 'error', message: '处理超时' });
              return;
            }
            try {
              const taskResp = await fetch(`/task/${taskId}`, { signal });
              const taskData = await taskResp.json();
              if (taskData.status === 'completed') {
                clearInterval(progressInterval);
                onProgress && onProgress(100);
                onStatus && onStatus({ status: 'done', chunks: taskData.chunks_stored, fileName: file.name });
                return;
              } else if (taskData.status === 'failed') {
                clearInterval(progressInterval);
                onStatus && onStatus({ status: 'error', message: taskData.message || '处理失败' });
                return;
              }
            } catch (err) {
              if (err.name === 'AbortError') return;
            }
            attempts++;
            await new Promise(r => setTimeout(r, Math.min(1500, 500 + attempts * 200)));
          }
          clearInterval(progressInterval);
          onStatus && onStatus({ status: 'error', message: '轮询次数耗尽' });
        } else {
          onStatus && onStatus({ status: 'error', message: '无效的响应' });
        }
      } else {
        onStatus && onStatus({ status: 'error', message: `上传失败 (${xhr.status})` });
      }
    });

    xhr.addEventListener('error', () => {
      onStatus && onStatus({ status: 'error', message: '网络错误' });
    });
    xhr.addEventListener('abort', () => {});

    const form = new FormData();
    form.append('file', file);
    xhr.send(form);

    return () => {
      xhr.abort();
      controller.abort();
    };
  }
};