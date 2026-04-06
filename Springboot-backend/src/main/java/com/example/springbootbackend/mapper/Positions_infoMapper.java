package com.example.springbootbackend.mapper;

import com.example.springbootbackend.entity.Positions_Info;
import org.apache.ibatis.annotations.*;

public interface Positions_infoMapper {
    @Select("SELECT * FROM positions_info where id = #{id}")
    Positions_Info getPositions_InfoById(Integer id);
    
    // 添加岗位信息
    @Insert("INSERT INTO positions_info (id, name, responsibilities, salary_junior, salary_mid, salary_senior, salary_expert, skill_requirements, create_time, update_time) VALUES (#{id}, #{name}, #{responsibility}, #{salary_junior}, #{salary_mid}, #{salary_senior}, #{salary_expert}, #{skill_requirements}, #{create_time}, #{update_time})")
    int addPositionInfo(Positions_Info positionInfo);
    
    // 更新岗位信息
    @Update("UPDATE positions_info SET name = #{name}, responsibilities = #{responsibility}, salary_junior = #{salary_junior}, salary_mid = #{salary_mid}, salary_senior = #{salary_senior}, salary_expert = #{salary_expert}, skill_requirements = #{skill_requirements}, update_time = #{update_time} WHERE id = #{id}")
    int updatePositionInfo(Positions_Info positionInfo);
    
    // 删除岗位信息
    @Delete("DELETE FROM positions_info WHERE id = #{id}")
    int deletePositionInfo(Integer id);
}