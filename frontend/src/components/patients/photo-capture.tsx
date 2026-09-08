"use client";

import React, { useRef, useState, useEffect } from "react";
import { Camera, Upload, Trash2, RefreshCw, CheckCircle, VideoOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

interface PhotoCaptureProps {
  value?: string;
  onChange: (photoDataUrl?: string) => void;
  patientName?: string;
}

export function PhotoCapture({ value, onChange, patientName = "Patient" }: PhotoCaptureProps) {
  const [isCameraOpen, setIsCameraOpen] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Stop camera media stream
  const stopCameraStream = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setIsStreaming(false);
  };

  // Open live webcam stream
  const startCamera = async () => {
    setCameraError(null);
    setIsCameraOpen(true);
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error("Camera API is not supported on this browser or environment.");
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: "user",
        },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
        setIsStreaming(true);
      }
    } catch (err: unknown) {
      console.warn("Camera error:", err);
      const msg =
        err instanceof Error
          ? err.message
          : "Could not access camera. Please verify camera permissions.";
      setCameraError(msg);
      setIsStreaming(false);
    }
  };

  // Capture current frame from video to canvas
  const captureFrame = () => {
    if (!videoRef.current) return;
    const video = videoRef.current;
    const canvas = document.createElement("canvas");
    canvas.width = 300;
    canvas.height = 300;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Square crop from center of video
    const minDim = Math.min(video.videoWidth || 300, video.videoHeight || 300);
    const startX = ((video.videoWidth || 300) - minDim) / 2;
    const startY = ((video.videoHeight || 300) - minDim) / 2;

    ctx.drawImage(video, startX, startY, minDim, minDim, 0, 0, 300, 300);
    const dataUrl = canvas.toDataURL("image/jpeg", 0.85);

    onChange(dataUrl);
    stopCameraStream();
    setIsCameraOpen(false);
  };

  // Handle local file upload
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      alert("Please upload a valid image file (JPEG, PNG, WebP).");
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      alert("File size exceeds 5MB limit.");
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      const dataUrl = event.target?.result as string;
      onChange(dataUrl);
    };
    reader.readAsDataURL(file);
    e.target.value = "";
  };

  // Clean up stream on unmount
  useEffect(() => {
    return () => {
      stopCameraStream();
    };
  }, []);

  const getInitials = (name: string) => {
    return name
      .split(" ")
      .map((part) => part[0])
      .filter(Boolean)
      .slice(0, 2)
      .join("")
      .toUpperCase() || "PT";
  };

  return (
    <div className="flex flex-col sm:flex-row items-center sm:items-start gap-4 p-4 rounded-xl border border-slate-200 bg-slate-50/70">
      {/* Circular Avatar / Photo Preview */}
      <div className="relative group shrink-0">
        <Avatar className="w-24 h-24 rounded-xl ring-2 ring-white shadow-sm border border-slate-200">
          <AvatarImage src={value || undefined} alt={patientName} className="object-cover" />
          <AvatarFallback className="rounded-xl bg-slate-200 text-slate-700 font-bold text-lg">
            {getInitials(patientName)}
          </AvatarFallback>
        </Avatar>
        {value && (
          <button
            type="button"
            onClick={() => onChange(undefined)}
            className="absolute -top-1 -right-1 p-1 bg-destructive text-white rounded-full shadow hover:bg-destructive/90 transition-colors"
            title="Remove Photo"
          >
            <Trash2 className="w-3 h-3" />
          </button>
        )}
      </div>

      {/* Action Buttons & Helpers */}
      <div className="flex-1 text-center sm:text-left space-y-2">
        <div>
          <h4 className="text-xs font-semibold text-slate-800">
            Patient Photograph <span className="text-slate-400 font-normal">(Optional)</span>
          </h4>
          <p className="text-[11px] text-slate-500">
            Capture live via clinical webcam or upload an ID photo (JPG/PNG max 5MB).
          </p>
        </div>

        <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2 pt-1">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={startCamera}
            className="gap-1.5 h-8 text-xs bg-white shadow-2xs hover:bg-slate-50"
          >
            <Camera className="w-3.5 h-3.5 text-primary" />
            Live Capture
          </Button>

          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => fileInputRef.current?.click()}
            className="gap-1.5 h-8 text-xs bg-white shadow-2xs hover:bg-slate-50"
          >
            <Upload className="w-3.5 h-3.5 text-slate-600" />
            Upload File
          </Button>

          {value && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => onChange(undefined)}
              className="gap-1 h-8 text-xs text-destructive hover:bg-destructive/10"
            >
              <Trash2 className="w-3 h-3" />
              Clear
            </Button>
          )}

          {/* Hidden File Input */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="hidden"
            onChange={handleFileUpload}
          />
        </div>
      </div>

      {/* Live Camera Dialog Modal */}
      <Dialog
        open={isCameraOpen}
        onOpenChange={(open) => {
          if (!open) {
            stopCameraStream();
          }
          setIsCameraOpen(open);
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base">
              <Camera className="w-4 h-4 text-primary" />
              Capture Patient Photo
            </DialogTitle>
            <DialogDescription className="text-xs">
              Position the patient facing the camera clearly within the center frame.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-2">
            <div className="relative aspect-video w-full rounded-lg bg-slate-950 overflow-hidden flex items-center justify-center">
              {cameraError ? (
                <div className="p-4 text-center text-slate-300 space-y-2">
                  <VideoOff className="w-8 h-8 mx-auto text-rose-400" />
                  <p className="text-xs font-medium text-rose-300">{cameraError}</p>
                  <p className="text-[11px] text-slate-400">
                    You can alternatively use the &quot;Upload File&quot; option to select a photo from local storage.
                  </p>
                </div>
              ) : (
                <>
                  <video
                    ref={videoRef}
                    autoPlay
                    playsInline
                    muted
                    className="w-full h-full object-cover"
                  />
                  {/* Overlay crosshair frame */}
                  <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
                    <div className="w-44 h-44 rounded-full border-2 border-dashed border-white/60 shadow-xs" />
                  </div>
                </>
              )}
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => {
                stopCameraStream();
                setIsCameraOpen(false);
              }}
            >
              Cancel
            </Button>

            {!cameraError && (
              <Button
                type="button"
                size="sm"
                onClick={captureFrame}
                disabled={!isStreaming}
                className="gap-1.5 bg-primary text-white hover:bg-primary/90"
              >
                <Camera className="w-4 h-4" />
                Capture Snapshot
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
