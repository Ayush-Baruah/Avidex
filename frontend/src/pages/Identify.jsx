import { useState } from 'react'

export default function Identify() {
    // Holds the actual File object selected from disk, or null if the
    // user is using the URL field instead.
    const [selectedFile, setSelectedFile] = useState(null)

    // A local preview URL for whichever image is currently selected --
    // either from the file input or typed into the URL field.
    const [previewUrl, setPreviewUrl] = useState(null)

    const [imageUrl, setImageUrl] = useState("")
    const [results, setResults] = useState(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)

    // Runs when the user picks a file from their computer.
    function handleFileChange(event) {
        const file = event.target.files[0]
        if (!file) return

        setSelectedFile(file)
        setImageUrl("")  // clear the URL field -- only one source at a time
        setPreviewUrl(URL.createObjectURL(file))
    }

    // Runs as the user types in the URL field.
    function handleUrlChange(event) {
        const value = event.target.value
        setImageUrl(value)
        setSelectedFile(null)  // clear the file -- only one source at a time
        setPreviewUrl(value || null)
    }

    async function handleSubmit(event) {
        event.preventDefault()
        setLoading(true)
        setError(null)
        setResults(null)

        // FormData, not JSON -- this is what lets us send either a real
        // file or a plain text URL field to the same backend route.
        const formData = new FormData()

        if (selectedFile) {
            formData.append("image", selectedFile)
        } else if (imageUrl) {
            formData.append("image_url", imageUrl)
        } else {
            setError("Please select a file or enter an image URL.")
            setLoading(false)
            return
        }

        try {
            const response = await fetch("http://localhost:8001/api/identify", {
                method: "POST",
                body: formData,
                // No Content-Type header here -- the browser sets the
                // correct multipart boundary automatically for FormData.
            })

            const data = await response.json()

            if (!response.ok) {
                setError(data.error || "Something went wrong.")
            } else {
                setResults(data.results)
            }
        } catch (err) {
            setError("Could not reach the server.")
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="identify-page">
            <h1 className='identify-title' >Identify a Bird</h1>

            <form className="image-form" onSubmit={handleSubmit}>
                <div className="form-row">
                    <label htmlFor="image_file">Upload a photo: </label>
                    <input
                        type="file"
                        id="image_file"
                        accept="image/*"
                        onChange={handleFileChange}
                    />
                </div>

                <p className='form-divider'>— or —</p>

                <div className="form-row">
                    <label htmlFor="image_url">Paste an image URL: </label>
                    <input
                        type="text"
                        id="image_url"
                        value={imageUrl}
                        onChange={handleUrlChange}
                        placeholder="https://..."
                    />
                </div>

                {previewUrl && (
                    <img src={previewUrl} alt="Preview" className="identify-preview" />
                )}

                <button className="form-submit" type="submit" disabled={loading}>
                    {loading ? "Identifying..." : "Identify"}
                </button>
            </form>

            {error && <p className="identify-error">{error}</p>}

            {results && (
                <div className="identify-results">
                    <h2>Top 5 Matches</h2>
                    <ol>
                        {results.map((result, index) => (
                            <li key={index}>
                                {/* bare folder-style name for now, per our plan to
                                    clean it up or enrich it from the DB later */}
                                {result.name.replace("_photos", "").replaceAll("_", " ")}
                                {" — "}
                                {(result.confidence * 100).toFixed(1)}%
                            </li>
                        ))}
                    </ol>
                </div>
            )}
        </div>
    )
}