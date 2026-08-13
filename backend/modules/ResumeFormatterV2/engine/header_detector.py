from engine.ai_header_detector import detect_header_ai

CALL_COUNT = 0

class HeaderDetector:

    def detect(self, lines, inside_employment=False):
        global CALL_COUNT
        CALL_COUNT += 1
        print(f"\n===== AI HEADER CALL #{CALL_COUNT} =====")
        print("\n".join(lines))
        return detect_header_ai(lines, inside_employment)

    def reset(self):
        global CALL_COUNT
        CALL_COUNT = 0


_detector = HeaderDetector()

print("******** USING AI HEADER DETECTOR ********")

def detect_header(lines, inside_employment=False):
    return _detector.detect(lines, inside_employment)

def reset_detector():
    _detector.reset()
