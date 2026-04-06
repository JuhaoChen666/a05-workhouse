package com.example.springbootbackend.mapper;

import com.example.springbootbackend.entity.Positions;
import org.apache.ibatis.annotations.*;
import java.util.List;
import java.util.Map;


@Mapper
public interface PositionsMapper {
    @Select("SELECT * FROM positions order by sort_order, id")
    List<Positions> getAllPositions();
    @Select("SELECT * FROM positions order by sort_order")
    List<Positions> getAllPositionsOrderBySortOrder();
    @Delete("DELETE FROM positions WHERE id = #{id}")
    int deletePosition(Integer id);
    
    // 分页查询和模糊查找
    @Select("SELECT * FROM positions WHERE name LIKE CONCAT('%', #{name}, '%') ORDER BY sort_order ASC LIMIT #{offset}, #{pageSize}")
    List<Positions> getPositionsByPage(@Param("name") String name, @Param("offset") int offset, @Param("pageSize") int pageSize);
    
    // 计算总数
    @Select("SELECT COUNT(*) FROM positions WHERE name LIKE CONCAT('%', #{name}, '%')")
    int countPositions(@Param("name") String name);
    
    // 添加岗位
    @Insert("INSERT INTO positions (name, sort_order) VALUES (#{name}, #{sort_order})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int addPosition(Positions position);

}