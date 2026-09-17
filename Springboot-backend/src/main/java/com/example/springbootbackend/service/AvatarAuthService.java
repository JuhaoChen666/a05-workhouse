package com.example.springbootbackend.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Base64;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;

@Service
public class AvatarAuthService {

    @Value("${avatar.api-key}")
    private String apiKey;

    @Value("${avatar.api-secret}")
    private String apiSecret;

    @Value("${avatar.app-id}")
    private String appId;

    @Value("${avatar.scene-id}")
    private String sceneId;

    public String getSignedUrl() throws Exception {
        String host = "avatar.cn-huadong-1.xf-yun.com";
        String path = "/v1/interact";
        
        SimpleDateFormat sdf = new SimpleDateFormat("EEE, dd MMM yyyy HH:mm:ss z", Locale.US);
        sdf.setTimeZone(TimeZone.getTimeZone("GMT"));
        String date = sdf.format(new Date());

        String signatureOrigin = "host: " + host + "\n" +
                                 "date: " + date + "\n" +
                                 "GET " + path + " HTTP/1.1";

        Mac mac = Mac.getInstance("HmacSHA256");
        SecretKeySpec spec = new SecretKeySpec(apiSecret.getBytes(StandardCharsets.UTF_8), "HmacSHA256");
        mac.init(spec);
        byte[] hexBytes = mac.doFinal(signatureOrigin.getBytes(StandardCharsets.UTF_8));
        String signature = Base64.getEncoder().encodeToString(hexBytes);

        String authorizationOrigin = String.format("api_key=\"%s\", algorithm=\"hmac-sha256\", headers=\"host date request-line\", signature=\"%s\"", 
                                      apiKey, signature);
        String authorization = Base64.getEncoder().encodeToString(authorizationOrigin.getBytes(StandardCharsets.UTF_8));

        return String.format("wss://%s%s?authorization=%s&date=%s&host=%s", 
                host, path, authorization, date.replace(" ", "%20"), host);
    }

    public String getAppId() {
        return appId;
    }

    public String getSceneId() {
        return sceneId;
    }
}
