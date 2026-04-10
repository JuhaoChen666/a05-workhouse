package com.example.springbootbackend.Controller;

import com.example.springbootbackend.entity.Positions;
import com.example.springbootbackend.entity.Positions_Info;
import com.example.springbootbackend.exception.ServiceException;
import com.example.springbootbackend.service.PositionsService;
import com.example.springbootbackend.utils.PermissionUtil;
import com.example.springbootbackend.utils.Result;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/positions")
public class PositionsController {
    @Autowired
    private PositionsService positionsService;

    @GetMapping
    public Result getAllPositions() {
        List<Positions> positions = positionsService.getAllPositions();
        return Result.success(positions);
    }

    @GetMapping("/{id}")
    public Result getPositionInfoById(@PathVariable Integer id) {
        Positions_Info positionInfo = positionsService.getPosition_InfoById(id);
        if (positionInfo == null) {
            return Result.resourceNotExist();
        }
        return Result.success(positionInfo);
    }
    
    // 简单分页查询(只返回id和name,按sort_order排序)
    @GetMapping("/simple/page")
    public Result getSimplePositionsByPage(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int pageSize,
            @RequestParam(required = false) String name) {
        // 如果有name参数,使用模糊查询
        if (name != null && !name.trim().isEmpty()) {
            Map<String, Object> result = positionsService.getSimplePositionsByPageWithName(name.trim(), page, pageSize);
            return Result.success(result);
        }
        // 否则使用普通分页查询
        Map<String, Object> result = positionsService.getSimplePositionsByPage(page, pageSize);
        return Result.success(result);
    }
}

