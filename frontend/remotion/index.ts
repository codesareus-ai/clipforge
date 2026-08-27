import { Composition } from "remotion";
import { CaptionedClip } from "./remotion/CaptionedClip";
import { clipProps } from "./remotion/defaultProps";

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
