package com.example.springbootbackend.Controller;

import com.example.springbootbackend.entity.Positions;
import com.example.springbootbackend.entity.Positions_Info;
import com.example.springbootbackend.service.PositionsService;
import com.example.springbootbackend.utils.Result;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

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
    public Result getPositionInfoById(@PathVariable int id) {
        Positions_Info positionInfo = positionsService.getPosition_InfoById(id);
        if (positionInfo == null) {
            return Result.resourceNotExist();
        }
        return Result.success(positionInfo);
    }
}
