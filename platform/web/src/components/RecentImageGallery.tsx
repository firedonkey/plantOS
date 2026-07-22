import { useMemo, useState } from "react";

import type { LatestImage } from "@/types";

type GalleryImage = Omit<LatestImage, "url"> & {
  url?: string;
};

type RecentImageGalleryProps = {
  images: GalleryImage[];
  captureDisabled?: boolean;
  captureLabel?: string;
  onCapture?: () => void;
};

export function RecentImageGallery({
  images,
  captureDisabled = false,
  captureLabel = "Capture image",
  onCapture,
}: RecentImageGalleryProps) {
  const [failedImageIds, setFailedImageIds] = useState<Set<string>>(() => new Set());
  const [selectedImageId, setSelectedImageId] = useState<string | null>(null);
  const latestImage = images[0];
  const recentImages = images.slice(0, 7);
  const selectedImage = useMemo(
    () => images.find((image) => image.id === selectedImageId) ?? latestImage,
    [images, latestImage, selectedImageId],
  );

  const markImageFailed = (imageId: string) => {
    setFailedImageIds((current) => {
      const next = new Set(current);
      next.add(imageId);
      return next;
    });
  };

  return (
    <div className="card stack-form image-gallery-panel">
      <div className="section-header">
        <div>
          <h3>Plant camera</h3>
          <p className="subtitle">
            {latestImage ? `${formatCameraRole(latestImage.cameraRole)} capture ${formatImageAge(latestImage.capturedAt)}` : "Watch new captures appear as the camera uploads them."}
          </p>
        </div>
        {onCapture ? (
          <button className="primary-button gallery-capture-button" disabled={captureDisabled} onClick={onCapture} type="button">
            {captureLabel}
          </button>
        ) : null}
      </div>

      {!images.length ? (
        <div className="image-gallery-empty">
          <div className="image-gallery-empty-mark" aria-hidden="true" />
          <div>
            <h4>No captures yet</h4>
            <p className="subtitle">The gallery will populate after the device uploads its next image.</p>
          </div>
        </div>
      ) : (
        <div className="image-gallery-layout">
          <figure className="image-gallery-hero">
            {selectedImage?.url && !failedImageIds.has(selectedImage.id) ? (
              <img
                alt="Selected PlantLab capture"
                src={selectedImage.url}
                onError={() => markImageFailed(selectedImage.id)}
              />
            ) : (
              <div className="image-gallery-fallback">
                <strong>{selectedImage?.url ? "Image unavailable" : "Loading image"}</strong>
                <span>{selectedImage?.url ? "The capture metadata is still available." : "Preparing the secure image preview."}</span>
              </div>
            )}
            <figcaption>
              <div>
                <span>{selectedImage?.id === latestImage?.id ? "Latest capture" : "Selected capture"}</span>
                <strong>{selectedImage ? `${formatCameraRole(selectedImage.cameraRole)} - ${formatImageAge(selectedImage.capturedAt)}` : "Waiting"}</strong>
              </div>
              <small>{selectedImage ? new Date(selectedImage.capturedAt).toLocaleString() : "No capture time"}</small>
            </figcaption>
          </figure>

          <aside className="image-gallery-rail" aria-label="Recent captures">
            <div className="image-gallery-rail-header">
              <strong>Recent captures</strong>
              <span>{images.length} image{images.length === 1 ? "" : "s"}</span>
            </div>
            <div className="image-gallery-thumbs">
              {recentImages.map((image) => {
                const active = selectedImage?.id === image.id;
                return (
                  <button
                    className={`image-gallery-thumb ${active ? "image-gallery-thumb-active" : ""}`}
                    key={image.id}
                    onClick={() => setSelectedImageId(image.id)}
                    type="button"
                  >
                    {image.url && !failedImageIds.has(image.id) ? (
                      <img alt="PlantLab capture thumbnail" src={image.url} onError={() => markImageFailed(image.id)} />
                    ) : (
                      <span>{image.url ? "Unavailable" : "Loading"}</span>
                    )}
                    <small>{formatCameraRole(image.cameraRole)} - {formatImageAge(image.capturedAt)}</small>
                  </button>
                );
              })}
            </div>
            {selectedImage ? (
              <div className="image-gallery-details">
                <span>Capture ID</span>
                <strong>{selectedImage.id}</strong>
                <span>Captured</span>
                <strong>{new Date(selectedImage.capturedAt).toLocaleString()}</strong>
                <span>Camera</span>
                <strong>{formatCameraRole(selectedImage.cameraRole)}</strong>
              </div>
            ) : null}
          </aside>
        </div>
      )}
    </div>
  );
}

function formatCameraRole(role: LatestImage["cameraRole"]) {
  if (role === "side") {
    return "Side";
  }
  return "Top";
}

function formatImageAge(timestamp: string) {
  const seconds = Math.max(0, Math.round((Date.now() - new Date(timestamp).getTime()) / 1000));
  if (seconds < 60) {
    return "just now";
  }
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) {
    return `${minutes}m ago`;
  }
  const hours = Math.round(minutes / 60);
  if (hours < 24) {
    return `${hours}h ago`;
  }
  const days = Math.round(hours / 24);
  return `${days}d ago`;
}
