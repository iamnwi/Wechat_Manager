/**
 * Created by ngwaii on 10/4/2018.
 */
import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.file.FileSystems;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.text.SimpleDateFormat;
import java.util.*;
import javax.crypto.spec.SecretKeySpec;
import javax.crypto.Mac;
// import sun.misc.BASE64Encoder;
import java.util.Base64;

@SuppressWarnings("restriction")
public class HttpUtil {
//    static Logger logger = LoggerFactory.getLogger(HttpUtil.class);
    /*
     * 计算MD5+BASE64
     */
    public static String MD5Base64(byte[] s) throws UnsupportedEncodingException {
        if (s == null){
            return null;
        }
        String encodeStr = "";
        //string 编码必须为utf-8
        MessageDigest mdTemp;
        try {
            mdTemp = MessageDigest.getInstance("MD5");
            mdTemp.update(s);
            byte[] md5Bytes = mdTemp.digest();
            // BASE64Encoder b64Encoder = new BASE64Encoder();
            // encodeStr = b64Encoder.encode(md5Bytes);
            // Encoder encoder = Base64.getEncoder();
            encodeStr = Base64.getEncoder().encodeToString(md5Bytes);
            /* java 1.8以上版本支持
            Encoder encoder = Base64.getEncoder();
            encodeStr = encoder.encodeToString(md5Bytes);
            */
        } catch (Exception e) {
            throw new Error("Failed to generate MD5 : " + e.getMessage());
        }
        return encodeStr;
    }
    /*
     * 计算 HMAC-SHA1
     */
    public static String HMACSha1(String data, String key) {
        String result;
        try {
            SecretKeySpec signingKey = new SecretKeySpec(key.getBytes(), "HmacSHA1");
            Mac mac = Mac.getInstance("HmacSHA1");
            mac.init(signingKey);
            byte[] rawHmac = mac.doFinal(data.getBytes());
            // result = (new BASE64Encoder()).encode(rawHmac);
            // Encoder encoder = Base64.getEncoder();
            result = Base64.getEncoder().encodeToString(rawHmac);
            /*java 1.8以上版本支持
            Encoder encoder = Base64.getEncoder();
            result = encoder.encodeToString(rawHmac);
            */
        } catch (Exception e) {
            throw new Error("Failed to generate HMAC : " + e.getMessage());
        }
        return result;
    }
    /*
     * 等同于javaScript中的 new Date().toUTCString();
     */
    public static String toGMTString(Date date) {
        SimpleDateFormat df = new SimpleDateFormat("E, dd MMM yyyy HH:mm:ss z", Locale.UK);
        df.setTimeZone(new java.util.SimpleTimeZone(0, "GMT"));
        return df.format(date);
    }
    /*
     * calc auth header
     */
    public static String EncryptAuthHeader(String audioPath, String audioFormat, String sampleRate, String ak_id, String ak_secret, String date) throws IOException {
        Path path = FileSystems.getDefault().getPath(audioPath);
        byte[] audioData = Files.readAllBytes(path);
        String method = "POST";
        String accept = "application/json";
        String content_type = "audio/"+audioFormat+";samplerate="+sampleRate;
        // String date = toGMTString(new Date());
        // 1.对body做MD5+BASE64加密
        String bodyMd5 = MD5Base64(audioData);
        // System.out.println(bodyMd5);
        String md52 = MD5Base64(bodyMd5.getBytes());
        // System.out.println(md52);
        String stringToSign = method + "\n" + accept + "\n" + md52 + "\n" + content_type + "\n" + date ;
        // 2.计算 HMAC-SHA1
        String signature = HMACSha1(stringToSign, ak_secret);
        // 3.得到 authorization header
        String authHeader = "Dataplus " + ak_id + ":" + signature;

        return authHeader;
    }
}
