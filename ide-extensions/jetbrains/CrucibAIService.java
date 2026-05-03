package com.crucibai;

import com.intellij.openapi.components.Service;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.wm.ToolWindow;
import com.intellij.openapi.wm.ToolWindowManager;
import com.intellij.util.messages.MessageBus;
import okhttp3.*;
import org.json.JSONObject;

import java.io.IOException;
import java.util.concurrent.TimeUnit;

/**
 * CrucibAI Service for JetBrains IDEs
 * Handles all API communication and core functionality
 */
@Service(Service.Level.PROJECT)
public final class CrucibAIService {

    private final Project project;
    private final OkHttpClient httpClient;
    private String apiUrl;
    private String apiKey;
    private boolean isConnected;

    public CrucibAIService(Project project) {
        this.project = project;
        this.httpClient = new OkHttpClient.Builder()
                .connectTimeout(30, TimeUnit.SECONDS)
                .readTimeout(30, TimeUnit.SECONDS)
                .writeTimeout(30, TimeUnit.SECONDS)
                .build();
        this.isConnected = false;
        initializeSettings();
    }

    /**
     * Initialize settings from configuration
     */
    private void initializeSettings() {
        CrucibAISettings settings = CrucibAISettings.getInstance();
        this.apiUrl = settings.getApiUrl();
        this.apiKey = settings.getApiKey();
    }

    /**
     * Generate code using AI
     */
    public String generateCode(String prompt, String context, String language) throws IOException {
        JSONObject payload = new JSONObject();
        payload.put("prompt", prompt);
        payload.put("context", context);
        payload.put("language", language);

        Response response = makeRequest("POST", "/api/generate", payload.toString());
        if (response.isSuccessful()) {
            JSONObject result = new JSONObject(response.body().string());
            return result.getString("code");
        }
        throw new IOException("Failed to generate code: " + response.code());
    }

    /**
     * Quick fix code issues
     */
    public String quickFix(String code, String language) throws IOException {
        JSONObject payload = new JSONObject();
        payload.put("code", code);
        payload.put("language", language);

        Response response = makeRequest("POST", "/api/fix", payload.toString());
        if (response.isSuccessful()) {
            JSONObject result = new JSONObject(response.body().string());
            return result.getString("fixed_code");
        }
        throw new IOException("Failed to fix code: " + response.code());
    }

    /**
     * Analyze code vibe
     */
    public JSONObject analyzeVibe(String code, String filePath) throws IOException {
        JSONObject payload = new JSONObject();
        payload.put("code", code);
        payload.put("file_path", filePath);

        Response response = makeRequest("POST", "/api/analyze-vibe", payload.toString());
        if (response.isSuccessful()) {
            return new JSONObject(response.body().string());
        }
        throw new IOException("Failed to analyze vibe: " + response.code());
    }

    /**
     * Process voice input
     */
    public JSONObject voiceInput(int duration) throws IOException {
        JSONObject payload = new JSONObject();
        payload.put("duration", duration);

        Response response = makeRequest("POST", "/api/voice-input", payload.toString());
        if (response.isSuccessful()) {
            return new JSONObject(response.body().string());
        }
        throw new IOException("Failed to process voice input: " + response.code());
    }

    /**
     * Generate tests
     */
    public String generateTests(String code, String language, String filePath) throws IOException {
        JSONObject payload = new JSONObject();
        payload.put("code", code);
        payload.put("language", language);
        payload.put("file_path", filePath);

        Response response = makeRequest("POST", "/api/generate-tests", payload.toString());
        if (response.isSuccessful()) {
            JSONObject result = new JSONObject(response.body().string());
            return result.getString("test_code");
        }
        throw new IOException("Failed to generate tests: " + response.code());
    }

    /**
     * Refactor code
     */
    public String refactorCode(String code, String language) throws IOException {
        JSONObject payload = new JSONObject();
        payload.put("code", code);
        payload.put("language", language);

        Response response = makeRequest("POST", "/api/refactor", payload.toString());
        if (response.isSuccessful()) {
            JSONObject result = new JSONObject(response.body().string());
            return result.getString("refactored_code");
        }
        throw new IOException("Failed to refactor code: " + response.code());
    }

    /**
     * Generate documentation
     */
    public String generateDocumentation(String code, String language, String filePath) throws IOException {
        JSONObject payload = new JSONObject();
        payload.put("code", code);
        payload.put("language", language);
        payload.put("file_path", filePath);

        Response response = makeRequest("POST", "/api/generate-docs", payload.toString());
        if (response.isSuccessful()) {
            JSONObject result = new JSONObject(response.body().string());
            return result.getString("documentation");
        }
        throw new IOException("Failed to generate documentation: " + response.code());
    }

    /**
     * Get code completions
     */
    public JSONObject getCompletions(String code, int position, String language) throws IOException {
        JSONObject payload = new JSONObject();
        payload.put("code", code);
        payload.put("position", position);
        payload.put("language", language);

        Response response = makeRequest("POST", "/api/completions", payload.toString());
        if (response.isSuccessful()) {
            return new JSONObject(response.body().string());
        }
        throw new IOException("Failed to get completions: " + response.code());
    }

    /**
     * Analyze code quality
     */
    public JSONObject analyzeCode(String code, String language, String filePath) throws IOException {
        JSONObject payload = new JSONObject();
        payload.put("code", code);
        payload.put("language", language);
        payload.put("file_path", filePath);

        Response response = makeRequest("POST", "/api/analyze", payload.toString());
        if (response.isSuccessful()) {
            return new JSONObject(response.body().string());
        }
        throw new IOException("Failed to analyze code: " + response.code());
    }

    /**
     * Test API connection
     */
    public boolean testConnection() {
        try {
            Response response = makeRequest("GET", "/api/health", null);
            this.isConnected = response.isSuccessful();
            return isConnected;
        } catch (IOException e) {
            this.isConnected = false;
            return false;
        }
    }

    /**
     * Make HTTP request to API
     */
    private Response makeRequest(String method, String endpoint, String body) throws IOException {
        Request.Builder requestBuilder = new Request.Builder()
                .url(apiUrl + endpoint)
                .addHeader("Authorization", "Bearer " + apiKey)
                .addHeader("Content-Type", "application/json");

        if ("POST".equals(method)) {
            requestBuilder.post(RequestBody.create(body, MediaType.get("application/json")));
        } else if ("GET".equals(method)) {
            requestBuilder.get();
        }

        Request request = requestBuilder.build();
        return httpClient.newCall(request).execute();
    }

    /**
     * Get project instance
     */
    public static CrucibAIService getInstance(Project project) {
        return project.getService(CrucibAIService.class);
    }

    /**
     * Check if connected to API
     */
    public boolean isConnected() {
        return isConnected;
    }

    /**
     * Update settings
     */
    public void updateSettings(String apiUrl, String apiKey) {
        this.apiUrl = apiUrl;
        this.apiKey = apiKey;
    }

    /**
     * Get tool window
     */
    public ToolWindow getToolWindow() {
        return ToolWindowManager.getInstance(project).getToolWindow("CrucibAI");
    }

    /**
     * Publish event to message bus
     */
    public void publishEvent(CrucibAIEvent event) {
        MessageBus messageBus = project.getMessageBus();
        messageBus.syncPublisher(CrucibAIEventListener.TOPIC).onEvent(event);
    }
}
