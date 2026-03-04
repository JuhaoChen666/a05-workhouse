package com.example.springbootbackend.utils;
import com.fasterxml.jackson.annotation.JsonPropertyOrder;
import lombok.Data;

import java.util.HashMap;
import java.util.Map;

/**
 * 封装通用返回类
 */
@Data
@JsonPropertyOrder({"code", "msg", "data"})
public class Result {
    //定义两个常量，成功的code是0，失败的是-1
    private static final String SUCCESS_CODE = "0";
    private static final String ERROR_CODE = "-1";


    private String code;//code：接口的响应结果
    private Object data;//data：数据
    private String msg;//msg：存放错误信息

    //无参数的成功方法，只返回成功代码“0”
    public static Result success() {
        Result result = new Result();
        result.setCode(SUCCESS_CODE);
        result.setMsg("ok");
        return result;
    }

    //有参数的成功方法，返回成功代码“0” 和 数据data
    public static Result success(Object data) {
        Result result = new Result();
        result.setCode(SUCCESS_CODE);
        result.setData(data);
        result.setMsg("ok");
        return result;
    }

    //失败的方法，返回自定义错误信息 和 错误代码“-1”
    public static Result error(String msg) {
        Result result = new Result();
        result.setCode(ERROR_CODE);
        result.setMsg(msg);
        return result;
    }

    //失败的方法，返回自定义错误信息 和 自定义错误代码
    public static Result error(String code, String msg) {
        Result result = new Result();
        result.setCode(code);
        result.setMsg(msg);
        return result;
    }

    //用户名或密码为空
    public static Result usernamePasswordEmpty() {
        return error("1001", "用户名或密码不能为空");
    }

    //两次密码不一致
    public static Result passwordNotMatch() {
        return error("1002", "两次密码不一致");
    }

    //用户名已存在
    public static Result usernameExist() {
        return error("1003", "用户名已存在");
    }

    //用户名或密码错误
    public static Result usernamePasswordError() {
        return error("1004", "用户名或密码错误");
    }
    //用户名不存在
    public static Result userNotExist() {
        return error("1005", "用户不存在");
    }
    //请求参数错误
    public static Result requestParamError() {
        return error("400", "请求参数错误");
    }
    //未提供token/token无效或已过期
    public static Result tokenNotProvidedOrInvalid() {
        return error("401", "未提供token或token无效或已过期");
    }
    //无权限
    public static Result noPermission() {
        return error("403", "无权限");
    }

    //资源不存在
    public static Result resourceNotExist() {
        return error("404", "资源不存在");
    }
    //服务器内部错误
    public static Result serverError() {
        return error("500", "服务器错误");
    }

    //添加数据到data字段
    public void addData(String key, Object value) {
        if (this.data == null) {
            this.data = new HashMap<>();
        }
        ((Map) this.data).put(key, value);
    }

}
