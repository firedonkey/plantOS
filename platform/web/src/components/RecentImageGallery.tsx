import { LatestImage } from "@/types";

type RecentImageGalleryProps = {
  images: LatestImage[];
};

export function RecentImageGallery({ images }: RecentImageGalleryProps) {
  return (
    <div className="card stack-form">
      <div className="section-header">
        <div>
          <h3>Recent image gallery</h3>
          <p className="subtitle">Recent uploads from the device appear here newest first. Manual capture is still coming later, so this gallery reflects images the device already sent.</p>
        </div>
      </div>

      {!images.length ? (
        <p className="subtitle">No image available yet. The gallery will populate after the device uploads its next image.</p>
      ) : (
        <div className="image-gallery-grid">
          {images.map((image) => (
            <figure className="image-gallery-card" key={image.id}>
              <img alt="Recent PlantLab capture" className="capture-image gallery-image" src={image.url} />
              <figcaption className="meta-text">Captured {new Date(image.capturedAt).toLocaleString()}</figcaption>
            </figure>
          ))}
        </div>
      )}
    </div>
  );
}
