import { Composition } from "remotion";
import { CaptionedClip } from "./CaptionedClip";
import { clipProps } from "./defaultProps";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="CaptionedClip"
        component={CaptionedClip}
        durationInFrames={180}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={clipProps}
      />
    </>
  );
};
