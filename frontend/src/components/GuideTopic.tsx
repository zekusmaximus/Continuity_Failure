import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  GUIDE_TOPICS,
  acknowledgeTopic,
  readAcknowledgedTopics,
  type GuideTopicId,
} from "../guide/topics";
import { useTelemetry } from "../telemetry/TelemetryProvider";

// Lets any phase open the complete Desk Guide from a topic callout without
// prop-drilling App's handler through every panel. Null (the default) simply
// hides the link — topics still teach and dismiss on their own.
const GuideContext = createContext<(() => void) | null>(null);

export function GuideProvider({
  openGuide,
  children,
}: {
  openGuide: () => void;
  children: ReactNode;
}) {
  return <GuideContext.Provider value={openGuide}>{children}</GuideContext.Provider>;
}

interface Props {
  topic: GuideTopicId;
  /** The taught object is on screen and matters right now. */
  active?: boolean;
}

/**
 * One contextual teaching callout — Wave 3 C1.
 *
 * Inline and non-modal by construction: it renders beside the object it
 * explains, never covers a primary action, never takes focus, and never
 * blocks resolution. It auto-shows once (until acknowledged, a versioned
 * local presentation preference) and stays reopenable afterward from a
 * compact affordance. Telemetry records topic ids only.
 */
export default function GuideTopic({ topic, active = true }: Props) {
  const copy = GUIDE_TOPICS[topic];
  const openGuide = useContext(GuideContext);
  const { report } = useTelemetry();

  const [acknowledged, setAcknowledged] = useState(
    () => readAcknowledgedTopics().has(topic),
  );
  const [reopened, setReopened] = useState(false);

  const visible = active && (!acknowledged || reopened);

  // One shown-event per appearance of an unacknowledged topic. The ref
  // survives StrictMode's double effect run.
  const reportedShown = useRef(false);
  useEffect(() => {
    if (!visible || acknowledged) {
      if (!visible) reportedShown.current = false;
      return;
    }
    if (reportedShown.current) return;
    reportedShown.current = true;
    report({ event_type: "guide_topic_shown", topic_id: topic });
  }, [visible, acknowledged, report, topic]);

  if (!active) return null;

  if (!visible) {
    return (
      <button
        type="button"
        className="cd-topic-reopen cd-linkbtn"
        onClick={() => {
          setReopened(true);
          report({ event_type: "guide_topic_opened", topic_id: topic });
        }}
      >
        ? About {copy.title.toLowerCase()}
      </button>
    );
  }

  const dismiss = () => {
    acknowledgeTopic(topic);
    setAcknowledged(true);
    setReopened(false);
  };

  return (
    <aside className="cd-guide-topic" role="note" aria-label={`Desk guide: ${copy.title}`}>
      <div className="cd-guide-topic-body">
        <span className="cd-guide-topic-title">{copy.title}</span>
        <p className="cd-guide-topic-text">{copy.body}</p>
      </div>
      <div className="cd-guide-topic-actions">
        <button type="button" className="cd-btn cd-btn-ghost cd-small" onClick={dismiss}>
          Got it
        </button>
        {openGuide && (
          <button
            type="button"
            className="cd-linkbtn"
            onClick={() => {
              report({ event_type: "guide_topic_opened", topic_id: topic });
              openGuide();
            }}
          >
            Open desk guide
          </button>
        )}
      </div>
    </aside>
  );
}
