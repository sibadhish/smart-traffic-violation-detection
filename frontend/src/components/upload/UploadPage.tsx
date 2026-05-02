import { useCallback, useRef, useState } from 'react';
import { Upload, FileVideo, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { uploadVideo, getTaskStatus, type ProcessingStatus } from '../../services/api';

type UploadState = 'idle' | 'uploading' | 'processing' | 'complete' | 'error';

export default function UploadPage() {
  const [state, setState] = useState<UploadState>('idle');
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [progress, setProgress] = useState<ProcessingStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<number | null>(null);

  const handleFile = (f: File) => {
    const allowedTypes = ['video/mp4', 'video/avi', 'video/quicktime', 'video/x-matroska', 'video/webm'];
    if (!allowedTypes.includes(f.type) && !f.name.match(/\.(mp4|avi|mov|mkv|webm)$/i)) {
      setError('Unsupported file type. Upload MP4, AVI, MOV, MKV, or WebM.');
      return;
    }
    setFile(f);
    setError(null);
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files?.[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  }, []);

  const pollStatus = useCallback((taskId: string) => {
    const poll = async () => {
      try {
        const status = await getTaskStatus(taskId);
        setProgress(status);

        if (status.status === 'SUCCESS') {
          setState('complete');
          if (pollRef.current) clearInterval(pollRef.current);
        } else if (status.status === 'FAILURE') {
          setState('error');
          setError(status.error || 'Processing failed');
          if (pollRef.current) clearInterval(pollRef.current);
        }
      } catch {
        // Keep polling on network errors
      }
    };

    pollRef.current = window.setInterval(poll, 2000);
    poll();
  }, []);

  const handleUpload = async () => {
    if (!file) return;

    setState('uploading');
    setError(null);

    try {
      const response = await uploadVideo(file);
      setState('processing');
      pollStatus(response.task_id);
    } catch (e) {
      setState('error');
      setError(e instanceof Error ? e.message : 'Upload failed');
    }
  };

  const handleReset = () => {
    setState('idle');
    setFile(null);
    setProgress(null);
    setError(null);
    if (pollRef.current) clearInterval(pollRef.current);
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Upload Video</h2>
      <p className="text-gray-600">
        Upload a traffic video for automated violation detection. Supported formats: MP4, AVI, MOV, MKV, WebM.
      </p>

      {/* Drop zone */}
      <div
        className={`relative rounded-lg border-2 border-dashed p-12 text-center transition-colors ${
          dragActive
            ? 'border-blue-500 bg-blue-50'
            : file
            ? 'border-green-300 bg-green-50'
            : 'border-gray-300 hover:border-gray-400'
        }`}
        onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        onClick={() => state === 'idle' && inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept="video/*"
          className="hidden"
          onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
        />

        {!file ? (
          <div className="space-y-3">
            <Upload className="mx-auto h-12 w-12 text-gray-400" />
            <p className="text-lg font-medium text-gray-700">
              Drag and drop a video file here
            </p>
            <p className="text-sm text-gray-500">or click to browse</p>
          </div>
        ) : (
          <div className="space-y-3">
            <FileVideo className="mx-auto h-12 w-12 text-green-500" />
            <p className="text-lg font-medium text-gray-700">{file.name}</p>
            <p className="text-sm text-gray-500">
              {(file.size / (1024 * 1024)).toFixed(1)} MB
            </p>
          </div>
        )}
      </div>

      {/* Error message */}
      {error && (
        <div className="flex items-center gap-2 rounded-md bg-red-50 p-4">
          <AlertCircle className="h-5 w-5 text-red-600" />
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {/* Progress */}
      {state === 'processing' && progress?.meta && (
        <div className="rounded-lg bg-white p-6 shadow">
          <div className="mb-4 flex items-center gap-3">
            <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
            <span className="font-medium text-gray-900">Processing video...</span>
          </div>
          <div className="mb-2 h-3 overflow-hidden rounded-full bg-gray-200">
            <div
              className="h-full rounded-full bg-blue-600 transition-all duration-500"
              style={{ width: `${progress.meta.progress_pct}%` }}
            />
          </div>
          <div className="flex justify-between text-sm text-gray-600">
            <span>Frames: {progress.meta.frames_processed.toLocaleString()} / {progress.meta.total_frames.toLocaleString()}</span>
            <span>Violations found: {progress.meta.violations_found}</span>
          </div>
        </div>
      )}

      {/* Complete */}
      {state === 'complete' && progress?.result && (
        <div className="rounded-lg bg-green-50 p-6">
          <div className="flex items-center gap-3">
            <CheckCircle className="h-6 w-6 text-green-600" />
            <span className="text-lg font-medium text-green-800">Processing complete</span>
          </div>
          <div className="mt-3 space-y-1 text-sm text-green-700">
            <p>Frames processed: {progress.result.frames_processed.toLocaleString()}</p>
            <p>Violations detected: {progress.result.violations_found}</p>
          </div>
          <a
            href="/violations"
            className="mt-4 inline-block rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
          >
            View Violations
          </a>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3">
        {state === 'idle' && file && (
          <button
            onClick={handleUpload}
            className="rounded-md bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Start Processing
          </button>
        )}
        {(state === 'complete' || state === 'error') && (
          <button
            onClick={handleReset}
            className="rounded-md bg-gray-200 px-6 py-2 text-sm font-medium text-gray-700 hover:bg-gray-300"
          >
            Upload Another
          </button>
        )}
      </div>
    </div>
  );
}
