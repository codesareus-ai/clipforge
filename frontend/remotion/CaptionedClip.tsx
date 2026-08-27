import { AbsoluteFill, useCurrentFrame, interpolate, Easing } from "remotion";

type Word = { text: string; start: number; end: number };
type Keyframe = { t: number; x: number; y: number; scale: number };
type Props = {
  clip: string;
  captions: Word[];
  reframe: Keyframe[];
  meta: { title: string; branding: string };
};

export const CaptionedClip: React.FC<Props> = ({ clip, captions, reframe, meta }) => {
  const frame = useCurrentFrame();
  const t = frame / 30; // seconds

  // --- smooth face-track reframe (keyframe interpolation) ---
  const kf = reframe && reframe.length ? reframe : [{ t: 0, x: 0.5, y: 0.5, scale: 1 }];
  let i = 0;
  while (i < kf.length - 1 && t > kf[i + 1].t) i++;
  const a = kf[i];
  const b = kf[Math.min(i + 1, kf.length - 1)];
  const span = Math.max(0.001, b.t - a.t);
  const f = Math.min(1, Math.max(0, (t - a.t) / span));
  const ease = Easing.inOut(Easing.cubic);
  const x = interpolate(f, [0, 1], [a.x, b.x], { easing: ease });
  const y = interpolate(f, [0, 1], [a.y, b.y], { easing: ease });
  const scale = interpolate(f, [0, 1], [a.scale, b.scale], { easing: ease });

  // --- karaoke captions: highlight the active word within a sliding window ---
  const activeIdx = captions.findIndex((w) => t >= w.start && t <= w.end);
  const windowWords = activeIdx >= 0
    ? captions.slice(Math.max(0, activeIdx - 6), activeIdx + 7)
    : [];

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      {clip ? (
        <video
          src={clip}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            transform: `scale(${scale})`,
            transformOrigin: `${x * 100}% ${y * 100}%`,
          }}
          autoPlay
          muted
        />
      ) : (
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", color: "white" }}>
          No clip
        </AbsoluteFill>
      )}

      <AbsoluteFill style={{ justifyContent: "flex-end", padding: 40 }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, maxWidth: "92%" }}>
          {windowWords.map((w, idx) => {
            const isActive = captions[activeIdx] === w;
            return (
              <span
                key={idx}
                style={{
                  fontSize: isActive ? 52 : 44,
                  fontWeight: isActive ? 900 : 700,
                  color: isActive ? "#FFD400" : "white",
                  textShadow: "0 2px 8px rgba(0,0,0,0.85)",
                  background: "rgba(0,0,0,0.45)",
                  padding: "4px 10px",
                  borderRadius: 10,
                }}
              >
                {w.text}
              </span>
            );
          })}
        </div>
      </AbsoluteFill>

      {meta.branding ? (
        <AbsoluteFill style={{ justifyContent: "flex-start", padding: 30 }}>
          <div style={{ fontSize: 28, color: "white", fontWeight: 700 }}>{meta.branding}</div>
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  );
};
