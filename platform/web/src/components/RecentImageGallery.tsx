import { LatestImage } from "@/types";

type RecentImageGalleryProps = {
  images: LatestImage[];
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
  const latestImage = images[0];
  const olderImages = images.slice(1, 4);

  return (
    <div className="card stack-form">
      <div className="section-header">
        <div>
          <h3>Camera</h3>
          <p className="subtitle">
            {latestImage ? `Latest capture ${formatImageAge(latestImage.capturedAt)}` : "Latest device captures appear here."}
          </p>
        </div>
        {onCapture ? (
          <button className="primary-button gallery-capture-button" disabled={captureDisabled} onClick={onCapture} type="button">
            {captureLabel}
          </button>
        ) : null}
      </div>

      {!images.length ? (
        <p className="subtitle">The gallery will populate after the device uploads its next capture.</p>
      ) : (
        <div className="image-gallery-stack">
          <figure className="image-gallery-card image-gallery-card-primary">
            <img alt="Recent PlantLab capture" className="capture-image gallery-image gallery-image-primary" src={latestImage.url} />
            <figcaption className="meta-text">Captured {new Date(latestImage.capturedAt).toLocaleString()}</figcaption>
          </figure>
          {olderImages.length ? (
            <div className="image-gallery-grid">
              {olderImages.map((image) => (
                <figure className="image-gallery-card" key={image.id}>
                  <img alt="Recent PlantLab capture" className="capture-image gallery-image" src={image.url} />
                  <figcaption className="meta-text">Captured {new Date(image.capturedAt).toLocaleString()}</figcaption>
                </figure>
              ))}
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
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
