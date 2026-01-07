"use client"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"
import { Mic, MicOff, Send, Volume2, VolumeX, Loader2 } from "lucide-react"
import Image from "next/image"

interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: Date
}

export default function Page() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "assistant",
      content:
        "Bonjour ! Je suis votre assistant virtuel Olifan. Je peux vous renseigner sur nos services d'ingénierie patrimoniale, d'investissement financier, de prévoyance et retraite, ainsi que sur nos solutions digitales. Comment puis-je vous aider aujourd'hui ?",
      timestamp: new Date(),
    },
  ])
  const [input, setInput] = useState("")
  const [isRecording, setIsRecording] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [queuePosition, setQueuePosition] = useState<number | null>(null)
  const [requestId, setRequestId] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const recognitionRef = useRef<any>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  // Initialize Speech Recognition
  useEffect(() => {
    if (typeof window !== "undefined" && ("webkitSpeechRecognition" in window || "SpeechRecognition" in window)) {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
      recognitionRef.current = new SpeechRecognition()
      recognitionRef.current.continuous = true  // Keep continuous for longer phrases
      recognitionRef.current.interimResults = true  // Enable interim results
      recognitionRef.current.lang = "fr-FR"  // French language support
      recognitionRef.current.maxAlternatives = 5  // Multiple alternatives
      
      let finalTranscript = "";
      
      // Add a timeout to prevent immediate stops
      let recognitionTimeout: NodeJS.Timeout | null = null;
      let startTime: number | null = null;  // Track when recognition started
      
      recognitionRef.current.onresult = (event: any) => {
        let interimTranscript = "";
        
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const result = event.results[i];
          if (result.isFinal) {
            finalTranscript += result[0].transcript;
          } else {
            interimTranscript += result[0].transcript;
          }
        }
        
        const currentTranscript = finalTranscript + interimTranscript;
        setInput(currentTranscript);
        
        // Clear any existing timeout and set a new one
        if (recognitionTimeout) {
          clearTimeout(recognitionTimeout);
        }
        
        // Set timeout to send after minimum time plus silence period
        const elapsed = startTime ? Date.now() - startTime : 0;
        const minTimeRemaining = Math.max(0, 6000 - elapsed);  // At least 6 seconds minimum
        
        recognitionTimeout = setTimeout(() => {
          setIsRecording(false);
          if (finalTranscript.trim()) {
            setInput(finalTranscript);
            setTimeout(() => {
              handleSend();
            }, 500);
          }
        }, minTimeRemaining + 2000); // Minimum time + 2 seconds of silence
      };
      
      recognitionRef.current.onnomatch = () => {
        console.log("Speech not recognized");
      };
      
      recognitionRef.current.onspeechend = () => {
        // When speech ends, send the message
        setIsRecording(false);
        if (finalTranscript.trim()) {
          setInput(finalTranscript);
          setTimeout(() => {
            handleSend();
          }, 500);
        }
        
        // Clear timeout if speech ends
        if (recognitionTimeout) {
          clearTimeout(recognitionTimeout);
        }
      };
      
      recognitionRef.current.onspeechstart = () => {
        console.log("Speech detected");
        // Record start time when speech begins
        startTime = Date.now();
        // Clear any existing timeout when speech starts
        if (recognitionTimeout) {
          clearTimeout(recognitionTimeout);
        }
      };
      
      // Add error handling
      recognitionRef.current.onerror = (event: any) => {
        console.error("Speech recognition error", event.error);
        setIsRecording(false);
        
        // Clear timeout on error
        if (recognitionTimeout) {
          clearTimeout(recognitionTimeout);
        }
      };
      
      recognitionRef.current.onend = () => {
        // Only set as stopped if not manually stopped
        if (isRecording) {
          setIsRecording(false);
        }
        
        // Clear timeout on end
        if (recognitionTimeout) {
          clearTimeout(recognitionTimeout);
        }
      }
    } else {
      console.warn("Speech Recognition not supported in this browser");
    }
  }, [])

  // Handle sending messages with queue support and better error handling
  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput("")
    setIsLoading(true)
    setQueuePosition(null)

    try {
      // Prepare chat history for API call
      const chatHistory = messages.map(msg => ({
        role: msg.role,
        content: msg.content
      }));

      // Use Render backend URL (update this with your actual Render URL)
      const backendUrl = 'https://olifane-group-agent.onrender.com';

      console.log('Connecting to backend:', backendUrl);

      // Call Olifan backend API with queue support
      const response = await fetch(`${backendUrl}/chat`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          message: userMessage.content,
          history: chatHistory
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('API Error Response:', errorText);
        throw new Error(`API Error: ${response.status} - ${errorText}`);
      }
      
      const data = await response.json();
      
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.response,
        timestamp: new Date(),
      }
      
      setMessages((prev) => [...prev, aiMessage])
      
    } catch (error: unknown) {
      console.error("API call failed:", error);
      
      // Show specific error message
      let errorMessageContent = "Désolé, je rencontre actuellement des difficultés techniques. ";
      
      if (error instanceof Error) {
        if (error instanceof TypeError && error.message.includes('fetch')) {
          errorMessageContent += "Impossible de se connecter au serveur. Veuillez vérifier que le backend est en cours d'exécution.";
        } else if (error.message.includes('404')) {
          errorMessageContent += "Le service n'est pas disponible. Veuillez réessayer plus tard.";
        } else {
          errorMessageContent += `Erreur: ${error.message}`;
        }
      } else {
        errorMessageContent += "Une erreur inconnue s'est produite.";
      }
      
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: errorMessageContent,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
      setQueuePosition(null)
      setRequestId(null)
    }
  }

  // Handle voice recording
  const toggleRecording = () => {
    if (!recognitionRef.current) {
      alert("Speech recognition is not supported in your browser. Please use Chrome or Edge for best speech recognition support.")
      return
    }

    try {
      if (isRecording) {
        recognitionRef.current.stop()
        setIsRecording(false)
      } else {
        // Clear input before starting recording
        setInput("")
        // Add a small delay to ensure proper initialization
        setTimeout(() => {
          recognitionRef.current.start()
          setIsRecording(true)
        }, 300)  // 300ms delay to prevent immediate cutoffs
      }
    } catch (error) {
      console.error("Speech recognition error:", error)
      setIsRecording(false)
      alert("Error starting speech recognition. Please check microphone permissions.")
    }
  }

  // Handle text-to-speech using Coqui TTS
  const speakMessage = async (text: string) => {
    if (isSpeaking) {
      setIsSpeaking(false)
      return
    }

    setIsSpeaking(true)
    
    try {
      // Call Coqui TTS API
      const response = await fetch('http://localhost:8000/tts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: text,
          language: 'fr'  // French language
        }),
      });

      if (!response.ok) {
        throw new Error(`TTS API error: ${response.status}`);
      }

      const data = await response.json();
      
      // Decode base64 audio and play
      const audioBytes = atob(data.audio);
      const audioBuffer = new ArrayBuffer(audioBytes.length);
      const audioArray = new Uint8Array(audioBuffer);
      
      for (let i = 0; i < audioBytes.length; i++) {
        audioArray[i] = audioBytes.charCodeAt(i);
      }
      
      // Create blob and play audio
      const audioBlob = new Blob([audioArray], { type: 'audio/wav' });
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      
      audio.onended = () => {
        setIsSpeaking(false);
        URL.revokeObjectURL(audioUrl);
      };
      
      audio.onerror = () => {
        setIsSpeaking(false);
        URL.revokeObjectURL(audioUrl);
      };
      
      await audio.play();
      
    } catch (error) {
      console.error("TTS Error:", error);
      setIsSpeaking(false);
      // Fallback to browser TTS if API fails
      fallbackToBrowserTTS(text);
    }
  };

  // Fallback to browser TTS if Coqui TTS fails
  const fallbackToBrowserTTS = (text: string) => {
    if (typeof window === "undefined") return;
    
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.85;
    utterance.pitch = 1.1;
    utterance.lang = "fr-FR";
    
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);
    
    window.speechSynthesis.speak(utterance);
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto px-3 py-3 sm:px-4 sm:py-4 md:py-6">
          <div className="flex flex-col items-center gap-2 sm:gap-3">
            <Image
              src="/olifan-logo.png"
              alt="Olifan Group"
              width={180}
              height={60}
              className="h-8 sm:h-10 md:h-12 w-auto"
              priority
            />
            <p className="text-xs sm:text-sm md:text-base text-muted-foreground text-center text-balance px-2">
              Leader français dans la gestion de patrimoine
            </p>
          </div>
        </div>
      </header>

      {/* Main Chat Interface */}
      <main className="container mx-auto px-3 sm:px-4 py-4 sm:py-6 md:py-8 max-w-4xl flex-1 flex flex-col">
        <Card className="shadow-lg border-border/40 flex-1 flex flex-col">
          <div className="flex flex-col h-full sm:h-[500px] md:h-[700px]">
            {/* Messages Container */}
            <div className="flex-1 overflow-y-auto p-3 sm:p-4 md:p-6 space-y-3 sm:space-y-4">
              {messages.map((message) => (
                <div key={message.id} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div
                    className={`max-w-[90%] sm:max-w-[85%] md:max-w-[75%] rounded-2xl px-3 py-2 sm:px-4 sm:py-3 ${
                      message.role === "user"
                        ? "bg-primary text-primary-foreground ml-auto"
                        : "bg-muted text-foreground"
                    }`}
                  >
                    <p className="text-sm sm:text-base leading-relaxed whitespace-pre-wrap">{message.content}</p>
                    {message.role === "assistant" && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="mt-2 h-7 px-2 text-xs hover:bg-background/10"
                        onClick={() => speakMessage(message.content)}
                      >
                        {isSpeaking ? (
                          <>
                            <VolumeX className="h-3 w-3 mr-1" />
                            Stop
                          </>
                        ) : (
                          <>
                            <Volume2 className="h-3 w-3 mr-1" />
                            Listen
                          </>
                        )}
                      </Button>
                    )}
                  </div>
                </div>
              ))}

              {/* Loading Indicator */}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-muted text-foreground max-w-[90%] sm:max-w-[85%] md:max-w-[75%] rounded-2xl px-3 py-2 sm:px-4 sm:py-3">
                    <div className="flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin text-primary" />
                      <span className="text-sm text-muted-foreground">
                        {queuePosition 
                          ? `Waiting in queue (position ${queuePosition})...` 
                          : "Processing your request..." 
                        }
                      </span>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="border-t border-border p-3 sm:p-4 md:p-6 bg-card/50">
              <div className="flex gap-2">
                <div className="flex-1 relative">
                  <Input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
                    placeholder="Type your message..."
                    className="pr-11 h-11 sm:h-12 text-sm sm:text-base"
                    disabled={isLoading}
                  />
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      className={`h-9 w-9 sm:h-10 sm:w-10 ${isRecording ? "text-primary" : ""}`}
                      onClick={toggleRecording}
                      disabled={isLoading}
                    >
                      {isRecording ? (
                        <MicOff className="h-4 w-4 sm:h-5 sm:w-5 animate-pulse" />
                      ) : (
                        <Mic className="h-4 w-4 sm:h-5 sm:w-5" />
                      )}
                    </Button>
                    {isRecording && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-9 w-9 sm:h-10 sm:w-10 text-green-500"
                        onClick={() => {
                          recognitionRef.current?.stop();
                          setIsRecording(false);
                          if (input.trim()) {
                            handleSend();
                          }
                        }}
                        disabled={isLoading}
                      >
                        <Send className="h-4 w-4 sm:h-5 sm:w-5" />
                      </Button>
                    )}
                  </div>
                </div>
                <Button
                  onClick={handleSend}
                  disabled={!input.trim() || isLoading}
                  size="icon"
                  className="h-11 w-11 sm:h-12 sm:w-12"
                >
                  <Send className="h-4 w-4 sm:h-5 sm:w-5" />
                </Button>
              </div>
              {isRecording && (
                <p className="text-xs text-muted-foreground mt-2 text-center animate-pulse">Listening... Speak now</p>
              )}
            </div>
          </div>
        </Card>

        <div className="mt-4 sm:mt-6 flex flex-wrap justify-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setInput("Qu'est-ce que l'ingénierie patrimoniale et comment pouvez-vous m'aider ?")}
            disabled={isLoading}
            className="text-xs h-8"
          >
            Ingénierie Patrimoniale
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setInput("Quels sont vos services d'investissement financier ?")}
            disabled={isLoading}
            className="text-xs h-8"
          >
            Investissement Financier
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setInput("Parlez-moi de vos solutions de prévoyance et retraite")}
            disabled={isLoading}
            className="text-xs h-8"
          >
            Prévoyance et Retraite
          </Button>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-border mt-auto py-4 sm:py-6 bg-card/30">
        <div className="container mx-auto px-3 sm:px-4">
          <p className="text-center text-xs sm:text-sm text-muted-foreground px-2">
            © {new Date().getFullYear()} Olifan Group – Leader français dans la gestion de patrimoine
          </p>
        </div>
      </footer>
    </div>
  )
}
