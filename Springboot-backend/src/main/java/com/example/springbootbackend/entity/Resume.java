package com.example.springbootbackend.entity;

import lombok.Data;
import java.util.Date;

@Data
public class Resume {
    private Long id;
    private Integer userId;
    private String filename;
    private String localPath;
    private String contentText;
    private Date uploadedAt;
}
