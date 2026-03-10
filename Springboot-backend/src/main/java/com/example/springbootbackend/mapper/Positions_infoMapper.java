package com.example.springbootbackend.mapper;

import com.example.springbootbackend.entity.Positions_Info;
import org.apache.ibatis.annotations.Select;

public interface Positions_infoMapper {
    @Select("SELECT * FROM positions_info where id = #{id}")
    Positions_Info getPositions_InfoById(Integer id);
}
