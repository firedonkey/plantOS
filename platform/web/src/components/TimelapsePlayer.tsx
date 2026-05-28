import { useEffect, useState } from "react";

import { DeviceTimelapse } from "@/types";

type TimelapsePlayerProps = {
  timelapse?: DeviceTimelapse;
};

export function TimelapsePlayer({ timelapse }: TimelapsePlayerProps) {
  const frames = timelapse?.frames ?? [];
  const [frameIndex, setFrameIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const currentFrame = frames[Math.min(frameIndex, Math.max(frames.length - 1, 0))];

  useEffect(() => {
    setFrameIndex(0);
    setPlaying(false);
  }, [timelapse?.windowStart, timelapse?.windowEnd, frames.length]);

  useEffect(() => {
    if (!playing || frames.length < 2) {
      return;
    }
    const intervalId = window.setInterval(() => {
      setFrameIndex((current) => (current + 1) % frames.length);
    }, timelapse?.playbackFrameMs ?? 450);
    return () => window.clearInterval(intervalId);
  }, [frames.length, playing, timelapse?.playbackFrameMs]);

  return (
    <section className="card stack-form">
      <div className="section-header">
        <div>
          <h3>Growth timelapse</h3>
          <p className="subtitle">{subtitleForTimelapse(timelapse)}</p>
        </div>
        {frames.length >= 2 ? (
          <div className="timelapse-actions">
            <button className="primary-button" onClick={() => setPlaying((current) => !current)} type="button">
              {playing ? "Pause" : "Play"}
            </button>
            <button
              className="secondary-button"
              onClick={() => {
                setFrameIndex(0);
                setPlaying(false);
              }}
              type="button"
            >
              Restart
            </button>
          </div>
        ) : null}
      </div>

      {!currentFrame ? (
        <p className="subtitle">PlantLab will build a timelapse after the camera has multiple captures over time.</p>
      ) : (
        <div className="timelapse-player">
          <img alt="PlantLab growth timelapse frame" className="capture-image timelapse-image" src={currentFrame.url} />
          <div className="timelapse-meta">
            <span>
              Frame {frameIndex + 1} of {frames.length}
            </span>
            <span>{new Date(currentFrame.capturedAt).toLocaleString()}</span>
          </div>
          {frames.length < 2 ? <p className="subtitle">One more capture is needed before playback is available.</p> : null}
        </div>
      )}
    </section>
  );
}

function subtitleForTimelapse(timelapse?: DeviceTimelapse): string {
  if (!timelapse || timelapse.frameCount === 0) {
    return "Sampled from the last week of camera captures.";
  }
  const imageWord = timelapse.totalImageCount === 1 ? "capture" : "captures";
  const frameWord = timelapse.frameCount === 1 ? "frame" : "frames";
  return `${timelapse.frameCount} ${frameWord} from ${timelapse.totalImageCount} ${imageWord}, sampled every ${formatInterval(timelapse.intervalMinutes)}.`;
}

function formatInterval(minutes: number): string {
  if (minutes < 60) {
    return `${minutes} min`;
  }
  const hours = minutes / 60;
  return Number.isInteger(hours) ? `${hours}h` : `${hours.toFixed(1)}h`;
}
