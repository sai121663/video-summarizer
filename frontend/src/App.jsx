import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import youtubeLogo from './assets/youtube-logo.png'
import remarkGfm from 'remark-gfm'
import '@fontsource/inter'
import '@fontsource/poppins'

function App() {

  // State variables
  const [url, setUrl] = useState("")
  const [level, setLevel] = useState("beginner")
  const [summary, setSummary] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [thumbnail, setThumbnail] = useState("")
  const [cachedTranscript, setCachedTranscript] = useState("")
  const [cachedThumbnail, setCachedThumbnail] = useState("")
  const [isPlaying, setIsPlaying] = useState(false)

  const handleURLChange = (e) => {
    setUrl(e.target.value)
    setCachedTranscript("")
    setThumbnail("")
  }

// Using Web Speech API instead of edge-tts
const handleReadAloud = () => {
  if (!summary) return
  
  if (isPlaying) {
    window.speechSynthesis.cancel()
    setIsPlaying(false)
  } else {
    const clean = cleanForSpeech(summary)
    const utterance = new SpeechSynthesisUtterance(clean)
    utterance.rate = 1
    utterance.pitch = 1
    utterance.onend = () => setIsPlaying(false)
    window.speechSynthesis.speak(utterance)
    setIsPlaying(true)
  }
}

  const cleanForSpeech = (text) => {
    let clean = text.replace(/#{1,6}\s*(.*)/g, '$1. ')  // headers
    clean = clean.replace(/(\d)️⃣/g, '$1. ')             // keycap emojis
    clean = clean.replace(/[*`_~|]/g, '')                // markdown symbols
    clean = clean.replace(/\n+/g, ' ')                   // newlines
    clean = clean.replace(/\s+/g, ' ')                   // extra spaces
    clean = clean.replace(/[\u{1F600}-\u{1F64F}]/gu, '') // emojis
    clean = clean.replace(/[\u{1F300}-\u{1F9FF}]/gu, '')
    clean = clean.replace(/[\u{2700}-\u{27BF}]/gu, '')
    return clean.trim()
  }

  // Runs when "summarize" button is clicked
    // Calls the /transcript endpoint & then sends the transcript to the /summarize endpoint
  const handleSubmit = async () => {
    
    // Stop playing the old audio when "Summarize" is clicked
    if (isPlaying) {
      window.speechSynthesis.cancel()
      setIsPlaying(false)
    }
    
    setLoading(true)
    setError("")
    setSummary("")
    setThumbnail("")
    setIsPlaying(false)

    try {
      let transcript = cachedTranscript

      // Only fetch the transcript if it's not already saved
        // Makes it faster if we want to change levels for the same video
      if (!transcript) {

        // Get the transcript directly from Flask backend
        const transcriptResponse = await fetch(`https://video-summarizer-backend-2jda.onrender.com/transcript?url=${encodeURIComponent(url)}`)
        const transcriptData = await transcriptResponse.json()

        if (transcriptData.error) {
          setError(transcriptData.error)
          setLoading(false)
          return
        }

        setThumbnail(transcriptData.thumbnail)
        setCachedThumbnail(transcriptData.thumbnail)
        setCachedTranscript(transcriptData.transcript)
        transcript = transcriptData.transcript

      } else {
        setThumbnail(cachedThumbnail)
      }
      

      // Summarize the transcript
      const summaryRes = await fetch("https://video-summarizer-backend-2jda.onrender.com/summarize", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({transcript: transcript, level})
      })

      // Get Claude's summary
      const summaryData = await summaryRes.json()

      // Error handling if the summary wasn't fetched properly
      if (summaryData.error) {
        setError(summaryData.error)
      } else {
        console.log("summary", summaryData.summary)
        setSummary(summaryData.summary)
      }

      // Error handling if the request fails (e.g. Flask isn't running)
    } catch (err) {
      console.log("Error: ", err)
      setError("ERROR: Please try again")
    }

    setLoading(false)
  }

return (
    <div style={{
      minHeight: "100vh",
      backgroundColor: "#0f0f0f",
      color: "#ffffff",
      fontFamily: "'Segoe UI', sans-serif",
      padding: "40px 20px"
    }}>
      <div style={{ maxWidth: "1200px", margin: "0 auto" }}>

        {/* Title */}
        <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "40px", justifyContent: "center" }}>
          <img src={youtubeLogo} alt="YouTube Logo" style={{ width: "50px" }} />
          <h1 style={{ margin: 0, fontSize: "28px", fontWeight: "700" }}>YouTube Video Summarizer</h1>
        </div>

        {/* Two column layout */}
        <div style={{ display: "flex", gap: "40px", alignItems: "flex-start" }}>

          {/* Left side - inputs */}
          <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center"}}>
            
            <input
              type="text"
              placeholder="Paste YouTube URL here"
              value={url}
              onChange={handleURLChange}
              style={{
                width: "100%",
                padding: "14px 16px",
                fontSize: "16px",
                fontFamily: "Poppins",
                borderRadius: "10px",
                border: "1px solid #333",
                backgroundColor: "#1a1a1a",
                color: "#ffffff",
                marginBottom: "16px",
                boxSizing: "border-box",
                outline: "none"
              }}
            />

            <select
              value={level}
              onChange={(e) => setLevel(e.target.value)}
              style={{
                padding: "12px 16px",
                fontSize: "16px",
                fontFamily: "Poppins",
                borderRadius: "10px",
                border: "1px solid #333",
                backgroundColor: "#1a1a1a",
                color: "#ffffff",
                marginBottom: "16px",
                cursor: "pointer",
                outline: "none",
                width: "100%"
              }}
            >
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="expert">Expert</option>
            </select>

            <button
              onClick={handleSubmit}
              disabled={loading}
              style={{
                padding: "12px 28px",
                fontSize: "16px",
                fontFamily: "Poppins",
                borderRadius: "10px",
                border: "none",
                backgroundColor: loading ? "#555" : "#ff0000",
                color: "#ffffff",
                cursor: loading ? "not-allowed" : "pointer",
                fontWeight: "600",
                transition: "background-color 0.2s",
                width: "100%"
              }}
            >
              {loading ? "Summarizing..." : "Summarize"}
            </button>

            {error && (
              <p style={{ color: "#ff4444", marginTop: "16px" }}>{error}</p>
            )}

          </div>

          {/* Right side - summary */}
          <div style={{ flex: 2, textAlign: "left" }}>
            {(loading || summary) && (
              <div style={{
                backgroundColor: "#1a1a1a",
                borderRadius: "12px",
                padding: "24px",
                lineHeight: "1.7",
                border: "1px solid #333",
                fontFamily: "'Inter', 'sans-serif'",
                minHeight: "200px"
              }}>

                <style>{`
                    @keyframes spin {from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

                    {/* Centers the title from the anthropic API response */}
                    .summary-content h1 {text-align: center; }

                    {/* Adds borders/grid lines to tables */}
                    .summary-content table { border-collapse: collapse; width: 100%; margin: 16px 0; }
                    .summary-content th, .summary-content td { border: 1px solid #444; padding: 8px 12px; text-align: left; }
                    .summary-content th { background-color: #2a2a2a; color: #ff0000; }
                `}</style>
                
                {/* Loading symbol */}
                {loading ? (
                  <>
                  <div style={{ display: "flex", alignItems: "center", gap: "12px", color: "#aaaaaa" }}>
                    <div style={{
                      width: "20px",
                      height: "20px",
                      border: "3px solid #333",
                      borderTop: "3px solid #ff0000",
                      borderRadius: "50%",
                      fontFamily: "Inter",
                      animation: "spin 1s linear infinite"
                    }}></div>
                    <span>Generating...</span>

                  </div>

                  {thumbnail && (
                      <img src={thumbnail} alt="Thumbnail" style={{
                        display: "block",
                        width: "80%", 
                        borderRadius: "10px", 
                        margin: "16px auto 0" 
                      }} />
                  )}

                </>
              ) : (
               
                <div className="summary-content">

                    {summary && (
                      <button
                        onClick={handleReadAloud}
                        style={{
                          padding: "12px 28px",
                          fontSize: "16px",
                          borderRadius: "10px",
                          border: "1px solid #ff0000",
                          backgroundColor: isPlaying ? "#cc0000" : "red",
                          color: audioLoading ? "red" : "black",
                          cursor: "pointer",
                          fontWeight: "600",
                          width: "100%",
                          marginTop: "10px",
                          fontFamily: "'Poppins', sans-serif"
                        }}
                      >
                        {isPlaying ? "⏸ Pause" : "🔊 Read Aloud"}
                      </button>
                    )}


                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{summary}</ReactMarkdown>
                </div> 
              )}

          </div>
        )}
      </div>

        </div>
      </div>
    </div>
  )
}

export default App