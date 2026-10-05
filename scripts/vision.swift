// Offline macOS OCR. Input: JSON array of image paths on stdin. Output: candidates per image.
import Foundation
import Vision
import ImageIO
do {
    let input = FileHandle.standardInput.readDataToEndOfFile()
    let paths = try JSONDecoder().decode([String].self, from: input)
    var results: [[[String: Any]]] = []
    for path in paths {
        let request = VNRecognizeTextRequest()
        request.recognitionLevel = .accurate
        request.usesLanguageCorrection = false
        request.recognitionLanguages = ["sv-SE", "en-US"]
        let handler = VNImageRequestHandler(url: URL(fileURLWithPath: path))
        try handler.perform([request])
        var candidates: [[String: Any]] = []
        for observation in request.results ?? [] {
            for candidate in observation.topCandidates(3) {
                candidates.append(["text": candidate.string, "confidence": candidate.confidence])
            }
        }
        results.append(candidates)
    }
    let data = try JSONSerialization.data(withJSONObject: results)
    FileHandle.standardOutput.write(data)
} catch {
    FileHandle.standardError.write(Data("\(error)\n".utf8))
    exit(1)
}
