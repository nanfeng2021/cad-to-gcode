"""
CAD to G-code Platform - Web API

FastAPI-based REST API for CAD processing and G-code generation.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Query, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, FileResponse, Response, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging
import uuid
from datetime import datetime

from src.config_loader import load_config
from src.core.process_planning import CuttingRulesEngine, MaterialType, OperationType
from src.cam.gcode_generator import GCodeGenerator, generate_simple_shaft
from src.storage.gcode_storage import GCodeDatabase
from src.ai.dxf_parser import DXFParser
from src.ai.feature_recognition import recognize_features
from src.storage.user_management import get_user_database, UserDatabase
from src.export.process_sheet import get_exporter
from src.core.batch_queue import BatchQueue, TaskPriority, TaskStatus
from src.core.tool_life_management import ToolLifeManager, Tool, ToolStatus as ToolLifeStatus
from src.core.cost_accounting import CostAccountingManager, CostType, CostCategory

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load configuration
config = load_config()

# Initialize FastAPI app
app = FastAPI(
    title="CAD to G-code Platform",
    description="AI-powered CAD to G-code generation for 2-axis CNC lathes",
    version=config["project"]["version"],
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize engines and database
cutting_engine = CuttingRulesEngine()
gcode_db = GCodeDatabase()
user_db = get_user_database()
batch_queue = BatchQueue()  # 批量处理队列
tool_life_manager = ToolLifeManager()  # 刀具寿命管理器
cost_manager = CostAccountingManager()  # 成本核算管理器

# 注册 DXF 到 G-code 的任务处理器
def process_dxf_to_gcode_task(payload: Dict) -> Dict:
    """处理 DXF 到 G-code 转换任务"""
    from src.ai.dxf_parser import parse_dxf_file
    from src.ai.feature_recognition import recognize_features
    from src.cam.gcode_generator import GCodeGenerator
    
    dxf_path = payload.get("dxf_path")
    material = payload.get("material", "45#钢")
    machine_system = payload.get("machine_system", "FANUC")
    
    # 解析 DXF
    entities = parse_dxf_file(dxf_path)
    
    # 特征识别
    features = recognize_features(entities)
    
    # G-code 生成
    generator = GCodeGenerator(material=material, machine_system=machine_system)
    gcode_lines = generator.generate_from_features(features)
    
    return {
        "features_count": len(features),
        "gcode_lines": len(gcode_lines),
        "material": material,
        "machine_system": machine_system
    }

batch_queue.register_handler("dxf_to_gcode", process_dxf_to_gcode_task)

# 启动后台工作线程（2 个工作者）
logger.info("Starting batch queue workers...")
batch_queue.start_worker(worker_id="worker_1", poll_interval=0.5)
batch_queue.start_worker(worker_id="worker_2", poll_interval=0.5)


# ==================== Models ====================

class MaterialInfo(BaseModel):
    """Material information response."""
    name: str
    code: str
    operations: List[str]


class CuttingParamsRequest(BaseModel):
    """Request for cutting parameters."""
    material: str = Field(..., description="Material type (e.g., '45#钢')")
    operation: str = Field(..., description="Operation type (e.g., '粗车')")
    tool_diameter: Optional[float] = Field(None, description="Tool diameter in mm")


class CuttingParamsResponse(BaseModel):
    """Cutting parameters response."""
    spindle_speed: int
    feed_rate: float
    depth_of_cut: float
    cutting_speed: Optional[int]
    material: str
    operation: str
    fanuc_code: str


class GCodeGenerationRequest(BaseModel):
    """G-code generation request."""
    start_diameter: float = Field(..., gt=0, description="Starting diameter in mm")
    end_diameter: float = Field(..., gt=0, description="Ending diameter in mm")
    length: float = Field(..., gt=0, description="Part length in mm")
    material: str = Field(default="45#钢", description="Material type")
    machine_system: str = Field(default="FANUC", description="CNC control system")


class GCodeGenerationResponse(BaseModel):
    """G-code generation response."""
    success: bool
    program_name: str
    gcode: str
    lines: int
    generated_at: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    timestamp: str
    config_loaded: bool
    materials_count: int
    programs_count: Optional[int] = None


class SaveProgramRequest(BaseModel):
    """Request to save a G-code program."""
    filename: str
    content: str
    material: str = Field(default="45#钢", description="Material type")
    operations: Optional[List[Dict]] = None
    metadata: Optional[Dict] = None


class SaveProgramResponse(BaseModel):
    """Response after saving a program."""
    success: bool
    program_id: int
    filename: str
    message: str


class ProgramSummary(BaseModel):
    """Program summary for list view."""
    id: int
    filename: str
    material: str
    created_at: str
    operation_count: int


class ProgramDetail(BaseModel):
    """Detailed program information."""
    id: int
    filename: str
    content: str
    material: str
    operations: List[Dict]
    created_at: str
    metadata: Optional[Dict] = None


class DXFUploadResponse(BaseModel):
    """Response after uploading and processing a DXF file."""
    success: bool
    filename: str
    features_count: int
    features: List[Dict]
    gcode: str
    gcode_lines: int
    program_name: str
    message: str


# ==================== Batch Processing Models ====================

class BatchTaskSubmitRequest(BaseModel):
    """批量任务提交请求"""
    task_type: str = Field(..., description="任务类型：dxf_to_gcode, batch_export, etc.")
    priority: int = Field(default=2, description="优先级：0=紧急，1=高，2=普通，3=低")
    payload: Dict[str, Any] = Field(..., description="任务参数")
    max_retries: int = Field(default=3, description="最大重试次数")


class BatchTaskSubmitResponse(BaseModel):
    """批量任务提交响应"""
    success: bool
    task_id: int
    message: str


class BatchTaskStatusResponse(BaseModel):
    """批量任务状态响应"""
    task_id: int
    task_type: str
    status: str
    priority: int
    progress: float
    result: Optional[Dict] = None
    error_message: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class BatchQueueStatusResponse(BaseModel):
    """批量队列状态响应"""
    total_tasks: int
    pending: int
    running: int
    completed: int
    failed: int
    avg_wait_time_seconds: float
    avg_process_time_seconds: float


class BatchTaskListResponse(BaseModel):
    """批量任务列表响应"""
    tasks: List[BatchTaskStatusResponse]
    total: int
    limit: int
    offset: int


class BatchDXFUploadRequest(BaseModel):
    """批量 DXF 上传请求"""
    files: List[str] = Field(..., description="DXF 文件路径列表")
    material: str = Field(default="45#钢", description="材料类型")
    machine_system: str = Field(default="FANUC", description="数控系统")
    priority: int = Field(default=2, description="优先级")


class BatchDXFUploadResponse(BaseModel):
    """批量 DXF 上传响应"""
    success: bool
    batch_id: str
    tasks_submitted: int
    task_ids: List[int]
    message: str


# ==================== Tool Life Management Models ====================

class ToolCreateRequest(BaseModel):
    """刀具创建请求"""
    tool_number: str = Field(..., min_length=4, description="刀具编号 (如 T0101)")
    name: str = Field(..., description="刀具名称")
    tool_type: str = Field(default="turning", description="刀具类型")
    model: str = Field(default="", description="型号")
    insert_material: str = Field(default="", description="刀片材料")
    insert_shape: str = Field(default="", description="刀片形状")
    manufacturer: str = Field(default="", description="制造商")
    supplier: str = Field(default="", description="供应商")
    unit_price: float = Field(default=0.0, description="单价（元）")
    max_life_minutes: int = Field(default=600, description="最大寿命（分钟）")
    life_warning_threshold: float = Field(default=0.2, description="寿命预警阈值")


class ToolResponse(BaseModel):
    """刀具响应"""
    id: int
    tool_number: str
    name: str
    tool_type: str
    model: str
    insert_material: str
    insert_shape: str
    manufacturer: str
    supplier: str
    unit_price: float
    max_life_minutes: int
    used_life_minutes: float
    remaining_life_minutes: float
    life_percentage: float
    usage_count: int
    total_parts: int
    status: str
    needs_replacement: bool
    estimated_cost_per_part: float
    install_date: Optional[str] = None
    last_maintenance_date: Optional[str] = None
    created_at: str


class ToolListResponse(BaseModel):
    """刀具列表响应"""
    tools: List[ToolResponse]
    total: int
    limit: int
    offset: int


class ToolUsageRecordRequest(BaseModel):
    """刀具使用记录请求"""
    program_name: str
    operation_type: str
    duration_minutes: float
    parts_count: int = Field(default=1, ge=1)
    wear_level: float = Field(default=0.0, ge=0.0, le=1.0)
    notes: Optional[str] = None


class ToolStatisticsResponse(BaseModel):
    """刀具统计响应"""
    total_tools: int
    available: int
    in_use: int
    worn: int
    avg_life_usage_percent: float
    total_parts_machined: int
    total_tool_cost: float
    tools_needing_replacement: int


class ToolWarningResponse(BaseModel):
    """刀具预警响应"""
    tool_id: int
    tool_number: str
    name: str
    life_percentage: float
    remaining_minutes: int
    severity: str
    message: str


# ==================== Cost Accounting Models ====================

class CostParameterResponse(BaseModel):
    """成本参数响应"""
    machine_hourly_rate: float
    labor_hourly_rate: float
    overhead_rate: float
    material_waste_factor: float
    default_tool_life_minutes: int


class CostRecordRequest(BaseModel):
    """成本记录请求"""
    program_name: str
    cost_type: str
    amount: float
    quantity: float = Field(default=1.0, ge=0)
    unit: str = Field(default="元", description="单位")
    category: str = Field(default="variable", description="成本分类")
    program_id: Optional[int] = None
    notes: Optional[str] = None


class CostRecordResponse(BaseModel):
    """成本记录响应"""
    id: int
    program_id: Optional[int]
    program_name: str
    cost_type: str
    category: str
    amount: float
    unit: str
    quantity: float
    total: float
    notes: Optional[str]
    created_at: str


class JobCostSummaryResponse(BaseModel):
    """任务成本汇总响应"""
    program_id: int
    program_name: str
    tool_cost: float
    material_cost: float
    machine_time_cost: float
    labor_cost: float
    overhead_cost: float
    maintenance_cost: float
    total_cost: float
    parts_count: int
    cost_per_part: float
    machining_time_minutes: float


class CostStatisticsResponse(BaseModel):
    """成本统计响应"""
    total_cost: float
    tool_cost: float
    material_cost: float
    machine_time_cost: float
    labor_cost: float
    overhead_cost: float
    job_count: int
    period_days: int


class MaterialPriceRequest(BaseModel):
    """材料价格请求"""
    material_name: str
    price_per_kg: float
    supplier: Optional[str] = None


class MaterialPriceResponse(BaseModel):
    """材料价格响应"""
    material_name: str
    price_per_kg: float
    supplier: Optional[str]
    updated_at: str


# ==================== User Models ====================

class UserLogin(BaseModel):
    """User login request."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class UserRegister(BaseModel):
    """User registration request."""
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    password: str = Field(..., min_length=6)


class UserResponse(BaseModel):
    """User information response."""
    id: int
    username: str
    email: str
    role: str


class LoginResponse(BaseModel):
    """Login response with token."""
    success: bool
    token: str
    user: UserResponse


class UserPreferences(BaseModel):
    """User preferences."""
    default_material: Optional[str] = None
    default_machine_system: Optional[str] = None
    theme: Optional[str] = None
    language: Optional[str] = None


# ==================== Endpoints ====================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "CAD to G-code Platform API",
        "version": config["project"]["version"],
        "description": "AI-powered CAD to G-code generation for 2-axis CNC lathes",
        "docs": "/docs",
        "health": "/health",
    }


# ==================== Authentication Dependency ====================

async def get_current_user(authorization: str = Header(None)) -> Optional[Dict]:
    """Get current user from JWT token."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    token = authorization.replace("Bearer ", "")
    user_info = user_db.verify_token(token)
    return user_info


async def require_auth(authorization: str = Header(None)) -> Dict:
    """Require authentication."""
    user_info = await get_current_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user_info


# ==================== User Authentication Endpoints ====================

@app.post("/auth/register", response_model=UserResponse, tags=["Authentication"])
async def register(request: UserRegister):
    """Register a new user."""
    try:
        user_id = user_db.create_user(
            username=request.username,
            email=request.email,
            password=request.password
        )
        
        if not user_id:
            raise HTTPException(status_code=400, detail="Username or email already exists")
        
        user = user_db.get_user_by_id(user_id)
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/auth/login", response_model=LoginResponse, tags=["Authentication"])
async def login(request: UserLogin):
    """Login and get JWT token."""
    try:
        result = user_db.authenticate(request.username, request.password)
        
        if not result:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        return LoginResponse(
            success=True,
            token=result['token'],
            user=UserResponse(**result['user'])
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error logging in: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/auth/logout", tags=["Authentication"])
async def logout(authorization: str = Header(None)):
    """Logout and invalidate token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="No token provided")
    
    token = authorization.replace("Bearer ", "")
    success = user_db.logout(token)
    
    return {"success": success}


@app.get("/auth/me", response_model=UserResponse, tags=["Authentication"])
async def get_current_user_info(current_user: dict = Depends(require_auth)):
    """Get current user information."""
    return UserResponse(
        id=current_user['user_id'],
        username=current_user['username'],
        email="",  # Don't expose email in this endpoint
        role=current_user['role']
    )


@app.get("/users/preferences", response_model=UserPreferences, tags=["Users"])
async def get_user_preferences(current_user: dict = Depends(require_auth)):
    """Get current user preferences."""
    prefs = user_db.get_user_preferences(current_user['user_id'])
    return UserPreferences(**prefs)


@app.post("/users/preferences", tags=["Users"])
async def update_user_preferences(
    preferences: UserPreferences,
    current_user: dict = Depends(require_auth)
):
    """Update user preferences."""
    success = user_db.update_user_preferences(
        current_user['user_id'],
        preferences.dict(exclude_none=True)
    )
    return {"success": success}


@app.get("/users", tags=["Users"])
async def list_users(current_user: dict = Depends(require_auth)):
    """List all users (admin only)."""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    users = user_db.list_users()
    return users


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version=config["project"]["version"],
        timestamp=datetime.now().isoformat(),
        config_loaded=True,
        materials_count=len(cutting_engine.list_materials()),
        programs_count=gcode_db.get_program_count()
    )


@app.get("/materials", response_model=List[MaterialInfo], tags=["Materials"])
async def list_materials():
    """List all supported materials."""
    materials = []
    for mat_name in cutting_engine.list_materials():
        ops = cutting_engine.list_operations(mat_name)
        mat_data = cutting_engine.rules.get(mat_name, {})
        materials.append(MaterialInfo(
            name=mat_name,
            code=mat_data.get("code", ""),
            operations=ops
        ))
    return materials


@app.post("/cutting-params", response_model=CuttingParamsResponse, tags=["Cutting Parameters"])
async def get_cutting_params(request: CuttingParamsRequest):
    """Get cutting parameters for a material and operation."""
    try:
        params = cutting_engine.get_params(
            request.material,
            request.operation,
            request.tool_diameter
        )
        
        return CuttingParamsResponse(
            spindle_speed=params.spindle_speed,
            feed_rate=params.feed_rate,
            depth_of_cut=params.depth_of_cut,
            cutting_speed=params.cutting_speed,
            material=params.material,
            operation=params.operation_type,
            fanuc_code=params.to_fanuc()
        )
    except Exception as e:
        logger.error(f"Error getting cutting params: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/gcode/generate", response_model=GCodeGenerationResponse, tags=["G-code"])
async def generate_gcode(request: GCodeGenerationRequest):
    """Generate G-code for a simple shaft turning operation."""
    try:
        gcode = generate_simple_shaft(
            start_diameter=request.start_diameter,
            end_diameter=request.end_diameter,
            length=request.length,
            material=request.material,
            machine_system=request.machine_system
        )
        
        lines = gcode.split("\n")
        program_name = f"O{uuid.uuid4().hex[:4].upper()}"
        filename = f"{program_name}.nc"
        
        # Save to database
        operations = [
            {"type": "rough_turn", "description": f"Rough turn from {request.start_diameter}mm to {request.end_diameter}mm"},
            {"type": "finish_turn", "description": f"Finish turn to final diameter {request.end_diameter}mm"}
        ]
        
        saved_id = gcode_db.save_program(
            filename=filename,
            content=gcode,
            material=request.material,
            operations=operations,
            metadata={
                "start_diameter": request.start_diameter,
                "end_diameter": request.end_diameter,
                "length": request.length,
                "machine_system": request.machine_system
            }
        )
        
        logger.info(f"Generated and saved G-code program ID: {saved_id}")
        
        return GCodeGenerationResponse(
            success=True,
            program_name=program_name,
            gcode=gcode,
            lines=len(lines),
            generated_at=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Error generating G-code: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/gcode/upload-dxf", response_model=DXFUploadResponse, tags=["G-code"])
async def upload_dxf_and_generate(
    file: UploadFile = File(..., description="DXF CAD file (.dxf)"),
    material: str = Form(default="45#钢", description="Material type"),
    machine_system: str = Form(default="FANUC", description="CNC control system"),
):
    """Upload a DXF file and generate G-code with feature recognition."""
    # Validate file extension
    if not file.filename.lower().endswith(".dxf"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.filename}. Only .dxf files are supported."
        )
    
    # Save uploaded file temporarily
    temp_dir = Path("/tmp/cad2gcode")
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_file = temp_dir / f"{uuid.uuid4()}.dxf"
    
    try:
        content = await file.read()
        temp_file.write_bytes(content)
        
        logger.info(f"Saved uploaded DXF to: {temp_file}")
        
        # Step 1: Parse DXF file
        parser = DXFParser()
        geometry = parser.parse_file(str(temp_file))
        
        logger.info(f"Parsed DXF: {len(geometry.lines)} lines, {len(geometry.texts)} texts")
        
        # Convert ParsedGeometry to entity list for feature recognition
        # Use object format for compatibility with feature recognition module
        entities = []
        
        # Helper classes for compatibility
        class Point2D:
            def __init__(self, x, z):
                self.x = x
                self.z = z
        
        class LineEntity:
            def __init__(self, start, end):
                self.type = 'LINE'
                self.start = start
                self.end = end
        
        # Process lines
        for line in geometry.lines:
            entities.append(LineEntity(
                Point2D(line.start.x, line.start.z),
                Point2D(line.end.x, line.end.z)
            ))
        
        # Also process polylines (convert to lines)
        for polyline in geometry.polylines:
            if len(polyline) >= 2:
                for i in range(len(polyline) - 1):
                    entities.append(LineEntity(
                        Point2D(polyline[i].x, polyline[i].z),
                        Point2D(polyline[i+1].x, polyline[i+1].z)
                    ))
        
        # Process circles
        class CircleEntity:
            def __init__(self, center, radius):
                self.type = 'CIRCLE'
                self.center = center
                self.radius = radius
        
        for circle in geometry.circles:
            entities.append(CircleEntity(
                Point2D(circle.center.x, circle.center.z),
                circle.radius
            ))
        
        # Process arcs
        class ArcEntity:
            def __init__(self, center, radius, start_angle, end_angle):
                self.type = 'ARC'
                self.center = center
                self.radius = radius
                self.start_angle = start_angle
                self.end_angle = end_angle
        
        for arc in geometry.arcs:
            entities.append(ArcEntity(
                Point2D(arc.center.x, arc.center.z),
                arc.radius,
                arc.start_angle,
                arc.end_angle
            ))
        
        # Step 2: Recognize machining features
        feature_result = recognize_features(entities)
        
        # Handle both dict and object return types
        if isinstance(feature_result, dict):
            features_list = feature_result.get('features', [])
            feature_objects = []
        else:
            features_list = []
            feature_objects = feature_result.features if hasattr(feature_result, 'features') else []
        
        # Convert feature objects to dicts if needed
        if feature_objects and not features_list:
            for idx, feat in enumerate(feature_objects):
                feat_dict = {
                    "id": idx + 1,  # Generate sequential ID
                    "type": feat.type.value if hasattr(feat.type, 'value') else str(feat.type),
                    "priority": 1,  # Default priority
                    "parameters": feat.parameters,
                    "machining_area": {
                        "start_x": feat.start_point[0] if feat.start_point else 0,
                        "start_z": feat.start_point[1] if feat.start_point else 0,
                        "end_x": feat.end_point[0] if feat.end_point else 0,
                        "end_z": feat.end_point[1] if feat.end_point else 0,
                    },
                    "confidence": feat.confidence,
                    "source": feat.source
                }
                features_list.append(feat_dict)
        
        logger.info(f"Recognized {len(features_list)} features")
        
        # Step 3: Generate G-code based on recognized features
        generator = GCodeGenerator(machine_system=machine_system)
        part_name = Path(file.filename).stem
        
        # Generate header
        program_name = f"O{uuid.uuid4().hex[:4].upper()}"
        generator.generate_header(program_name=program_name, part_name=part_name)
        
        # Safety startup
        generator._add_block("G21", "Metric units")
        generator._add_block("G40 G97 G99", "Cancel compensation, constant RPM, feed per rev")
        generator._add_block("G00 X0 Z5", "Rapid to start position")
        
        # Find maximum diameter for stock from features
        max_diameter = 50.0
        for feat in features_list:
            if feat.get('type') == 'external_cylinder':
                dia = feat.get('parameters', {}).get('diameter', 0)
                if dia > max_diameter:
                    max_diameter = dia
        
        total_length = 100.0
        for feat in features_list:
            params = feat.get('parameters', {})
            z_end = abs(params.get('end_z', 0) or params.get('start_z', 0))
            if z_end > total_length:
                total_length = z_end
        
        stock_diameter = max_diameter + 5
        
        # Facing operation
        generator._add_block("T0101 M06", "Face tool")
        generator._add_block("S800 M03", "Spindle on CW")
        generator._add_block(f"G00 X{stock_diameter} Z0 M08", "Rapid to facing start")
        generator._add_block("G01 X-2 F0.2", "Face to center")
        generator._add_block(f"G00 X{stock_diameter} Z2", "Retract")
        
        # Rough turning using G71 cycle
        generator._add_block("T0202 M06", "Rough turning tool")
        generator._add_block(f"G00 X{stock_diameter} Z2", "Rapid to cycle start")
        generator._add_block("G71 U2.0 R0.5", "Rough cycle - depth of cut 2mm")
        generator._add_block(f"G71 P10 Q20 U0.5 W0.2 F0.3", "Rough cycle - finish allowance 0.5mm")
        
        # Generate profile from features
        generator._add_block("N10 G00 X0", "Start of profile")
        
        # Sort features by Z position (from 0 to negative)
        sorted_features = sorted(
            [f for f in features_list if f.get('type') in ['external_cylinder', 'taper']],
            key=lambda f: abs(f.get('parameters', {}).get('end_z', 0) or f.get('parameters', {}).get('start_z', 0))
        )
        
        current_x = 0
        for i, feat in enumerate(sorted_features):
            if feat.get('type') == 'external_cylinder':
                params = feat.get('parameters', {})
                dia = params.get('diameter', current_x * 2)
                z_end = params.get('end_z', params.get('start_z', 0))
                generator._add_block(
                    f"G01 X{dia} Z{z_end} F0.2",
                    f"Turn to Ø{dia}mm at Z{z_end}"
                )
                current_x = dia / 2
            elif feat.get('type') == 'taper':
                params = feat.get('parameters', {})
                start_dia = params.get('start_diameter', current_x * 2)
                end_dia = params.get('end_diameter', start_dia)
                z_end = params.get('end_z', params.get('start_z', 0))
                generator._add_block(
                    f"G01 X{end_dia} Z{z_end} F0.2",
                    f"Taper to Ø{end_dia}mm at Z{z_end}"
                )
                current_x = end_dia / 2
        
        generator._add_block(f"N20 G01 X{stock_diameter}", "End of profile")
        
        # Finish turning
        generator._add_block("T0303 M06", "Finish turning tool")
        generator._add_block("S1200 M03", "Higher speed for finish")
        generator._add_block(f"G00 X{max_diameter} Z2", "Rapid to finish start")
        generator._add_block("G70 P10 Q20 F0.1", "Finish cycle")
        
        # Groove operations (if any)
        groove_features = [f for f in features_list if f.get('type') == 'groove']
        if groove_features:
            generator._add_block("T0404 M06", "Grooving tool")
            for groove in groove_features:
                params = groove.get('parameters', {})
                width = params.get('width', 3.0)
                depth = params.get('depth', 2.0)
                pos_z = params.get('position_z', -40.0)
                groove_dia = params.get('groove_diameter', 46.0)
                
                generator._add_block(f"S600 M03", "Lower speed for grooving")
                generator._add_block(f"G00 X{groove_dia + 5} Z{pos_z}", "Position at groove")
                generator._add_block(f"G01 X{groove_dia} F0.1", "Plunge to groove depth")
                generator._add_block(f"G00 X{groove_dia + 5}", "Retract")
        
        # Thread operations (if any)
        thread_features = [f for f in features_list if f.get('type') == 'thread']
        if thread_features:
            generator._add_block("T0505 M06", "Threading tool")
            for thread in thread_features:
                params = thread.get('parameters', {})
                major_dia = params.get('major_diameter', 30.0)
                minor_dia = params.get('minor_diameter', 28.0)
                pitch = params.get('pitch', 1.5)
                start_z = params.get('start_z', -43.0)
                length = params.get('length', 20.0)
                
                generator._add_block(f"S400 M03", "Low speed for threading")
                generator._add_block(f"G00 X{major_dia + 5} Z{start_z + 5}", "Rapid to thread start")
                generator._add_block(
                    f"G76 P020060 Q100 R0.05",
                    "Threading cycle params"
                )
                thread_depth = int((major_dia - minor_dia) / 2 * 1000)
                generator._add_block(
                    f"G76 X{minor_dia:.3f} Z{start_z - length:.3f} P{thread_depth:04d} Q100 F{pitch:.3f}",
                    f"Thread {params.get('designation', 'M30x1.5')}"
                )
        
        # Program end
        generator._add_block("G00 X100 Z100", "Rapid to change position")
        generator.generate_footer()
        
        # Get G-code
        gcode = generator.generate()
        lines = gcode.split('\n')
        
        # Save to database
        saved_id = gcode_db.save_program(
            filename=f"{program_name}.nc",
            content=gcode,
            material=material,
            operations=[{"type": f.get('type'), "parameters": f.get('parameters', {})} for f in features_list],
            metadata={
                "source_file": file.filename,
                "feature_count": len(features_list),
                "machine_system": machine_system
            }
        )
        
        logger.info(f"Generated and saved G-code program ID: {saved_id}")
        
        return DXFUploadResponse(
            success=True,
            filename=file.filename,
            features_count=len(features_list),
            features=features_list,
            gcode=gcode,
            gcode_lines=len(lines),
            program_name=program_name,
            message=f"Successfully processed {file.filename}: {len(features_list)} features recognized"
        )
    
    except Exception as e:
        logger.error(f"Error processing DXF: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))
    
    finally:
        # Cleanup
        if temp_file.exists():
            temp_file.unlink()


@app.get("/programs", response_model=List[ProgramSummary], tags=["Programs"])
async def list_programs(
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(require_auth)
):
    """List user's saved G-code programs with pagination."""
    try:
        # Only show user's own programs (admin can see all)
        user_id = None if current_user['role'] == 'admin' else current_user['user_id']
        
        programs = gcode_db.list_programs(limit=limit, offset=offset, user_id=user_id)
        return [
            ProgramSummary(
                id=p["id"],
                filename=p["filename"],
                material=p["material"],
                created_at=p["created_at"],
                operation_count=len(p.get("operations", []))
            )
            for p in programs
        ]
    except Exception as e:
        logger.error(f"Error listing programs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/programs/search", tags=["Programs"])
async def search_programs(
    q: str,
    limit: int = 20,
    current_user: dict = Depends(require_auth)
):
    """Search user's programs by filename or material."""
    try:
        # Only search user's own programs (admin can search all)
        user_id = None if current_user['role'] == 'admin' else current_user['user_id']
        
        programs = gcode_db.search_programs(query=q, limit=limit, user_id=user_id)
        return [
            {
                "id": p["id"],
                "filename": f"{p['program_name']}.nc",
                "material": p["material"],
                "created_at": p["created_at"],
                "operation_count": 0  # Simplified for search results
            }
            for p in programs
        ]
    except Exception as e:
        logger.error(f"Error searching programs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/programs/{program_id}", response_model=ProgramDetail, tags=["Programs"])
async def get_program(program_id: int):
    """Get a specific G-code program by ID."""
    try:
        program = gcode_db.get_program(program_id)
        if not program:
            raise HTTPException(status_code=404, detail=f"Program {program_id} not found")
        
        return ProgramDetail(
            id=program["id"],
            filename=program["filename"],
            content=program["content"],
            material=program["material"],
            operations=program.get("operations", []),
            created_at=program["created_at"],
            metadata=program.get("metadata", {})
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting program {program_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/programs/{program_id}/download", tags=["Programs"])
async def download_program(program_id: int):
    """Download a G-code program as .nc file."""
    try:
        program = gcode_db.get_program(program_id)
        if not program:
            raise HTTPException(status_code=404, detail=f"Program {program_id} not found")
        
        return PlainTextResponse(
            content=program["content"],
            media_type="text/plain",
            headers={"Content-Disposition": f'attachment; filename="{program["filename"]}"'}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading program {program_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/programs/{program_id}/export/pdf", tags=["Export"])
async def export_program_pdf(program_id: int, current_user: dict = Depends(require_auth)):
    """Export program as PDF process sheet."""
    try:
        program = gcode_db.get_program(program_id)
        if not program:
            raise HTTPException(status_code=404, detail=f"Program {program_id} not found")
        
        # Check ownership (admin can export any program)
        if current_user['role'] != 'admin' and program.get('user_id') != current_user['user_id']:
            raise HTTPException(status_code=403, detail="You don't have permission to export this program")
        
        exporter = get_exporter()
        pdf_bytes = exporter.generate_pdf(program)
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{program["filename"].replace(".nc", "")}_process_sheet.pdf"'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting PDF for program {program_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/programs/{program_id}/export/html", tags=["Export"])
async def export_program_html(program_id: int):
    """Export program as HTML process sheet."""
    try:
        program = gcode_db.get_program(program_id)
        if not program:
            raise HTTPException(status_code=404, detail=f"Program {program_id} not found")
        
        exporter = get_exporter()
        html_content = exporter.generate_html(program)
        
        return HTMLResponse(content=html_content)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting HTML for program {program_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/programs/{program_id}", tags=["Programs"])
async def delete_program(program_id: int):
    """Delete a G-code program."""
    try:
        success = gcode_db.delete_program(program_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Program {program_id} not found")
        return {"message": f"Program {program_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting program {program_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/programs/{program_id}/content", tags=["Programs"])
async def update_program_content(
    program_id: int,
    request: dict,
    current_user: dict = Depends(require_auth)
):
    """Update G-code program content (user-specific)."""
    try:
        content = request.get('content', '')
        if not content:
            raise HTTPException(status_code=400, detail="Content is required")
        
        # Check if program exists and belongs to user (or user is admin)
        conn = gcode_db._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM programs WHERE id = ?", (program_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Program {program_id} not found")
        
        # Check ownership (admin can edit any program)
        if current_user['role'] != 'admin' and row[0] != current_user['user_id']:
            conn.close()
            raise HTTPException(status_code=403, detail="You don't have permission to edit this program")
        
        # Update content
        cursor.execute("""
            UPDATE programs SET content = ? WHERE id = ?
        """, (content, program_id))
        conn.commit()
        conn.close()
        
        logger.info(f"Updated program {program_id} content, user: {current_user['username']}")
        
        return {
            "success": True,
            "program_id": program_id,
            "message": f"Program {program_id} content updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating program {program_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/programs", response_model=SaveProgramResponse, tags=["Programs"])
async def save_program(
    request: SaveProgramRequest,
    current_user: dict = Depends(require_auth)
):
    """Save a G-code program to the database (user-specific)."""
    try:
        saved_id = gcode_db.save_program(
            filename=request.filename,
            content=request.content,
            material=request.material,
            operations=request.operations or [],
            metadata=request.metadata,
            user_id=current_user['user_id']
        )
        
        logger.info(f"Saved G-code program ID: {saved_id}, filename: {request.filename}, user: {current_user['username']}")
        
        return SaveProgramResponse(
            success=True,
            program_id=saved_id,
            filename=request.filename,
            message=f"Program saved successfully with ID {saved_id}"
        )
    except Exception as e:
        logger.error(f"Error saving program: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/gcode/{program_id}", tags=["G-code"])
async def get_gcode_program(program_id: str):
    """Get a previously generated G-code program by ID."""
    # TODO: Implement program storage and retrieval
    raise HTTPException(status_code=404, detail="Program not found")


@app.post("/gcode/{program_id}/download", tags=["G-code"])
async def download_gcode(program_id: str):
    """Download G-code program as a file."""
    # TODO: Implement program download
    raise HTTPException(status_code=404, detail="Program not found")


@app.get("/machine-systems", tags=["Configuration"])
async def list_machine_systems():
    """List supported CNC machine control systems."""
    systems = []
    for system_name, data in cutting_engine.machine_systems.items():
        systems.append({
            "name": system_name,
            "standard": data.get('g_code_standard', ''),
            "m_codes": data.get('m_codes', {}),
        })
    return {"systems": systems}


# ==================== Batch Processing Endpoints ====================

@app.post("/batch/submit", tags=["Batch Processing"])
async def submit_batch_task(request: BatchTaskSubmitRequest):
    """提交批量处理任务"""
    try:
        task_id = batch_queue.submit_task(
            task_type=request.task_type,
            payload=request.payload,
            priority=request.priority,
            max_retries=request.max_retries
        )
        
        return BatchTaskSubmitResponse(
            success=True,
            task_id=task_id,
            message=f"Task submitted successfully with ID {task_id}"
        )
    except Exception as e:
        logger.error(f"Error submitting batch task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/batch/dxf-upload", tags=["Batch Processing"])
async def batch_upload_dxf(request: BatchDXFUploadRequest):
    """批量上传 DXF 文件并生成 G-code"""
    try:
        task_ids = []
        for file_path in request.files:
            task_id = batch_queue.submit_task(
                task_type="dxf_to_gcode",
                payload={
                    "dxf_path": file_path,
                    "material": request.material,
                    "machine_system": request.machine_system
                },
                priority=request.priority
            )
            task_ids.append(task_id)
        
        batch_id = f"batch_{uuid.uuid4().hex[:8]}"
        
        return BatchDXFUploadResponse(
            success=True,
            batch_id=batch_id,
            tasks_submitted=len(task_ids),
            task_ids=task_ids,
            message=f"Submitted {len(task_ids)} tasks for batch processing"
        )
    except Exception as e:
        logger.error(f"Error in batch DXF upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/batch/status/{task_id}", tags=["Batch Processing"])
async def get_task_status(task_id: int):
    """获取任务状态"""
    task = batch_queue.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    return BatchTaskStatusResponse(
        task_id=task.id,
        task_type=task.task_type,
        status=task.status,
        priority=task.priority,
        progress=task.progress,
        result=task.result,
        error_message=task.error_message,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at
    )


@app.get("/batch/queue-status", tags=["Batch Processing"])
async def get_queue_status():
    """获取队列状态"""
    status = batch_queue.get_queue_status()
    return BatchQueueStatusResponse(**status)


@app.get("/batch/tasks", tags=["Batch Processing"])
async def list_batch_tasks(
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0)
):
    """列出批量任务"""
    tasks = batch_queue.list_tasks(
        status=status,
        task_type=task_type,
        limit=limit,
        offset=offset
    )
    
    task_responses = [
        BatchTaskStatusResponse(
            task_id=t.id,
            task_type=t.task_type,
            status=t.status,
            priority=t.priority,
            progress=t.progress,
            result=t.result,
            error_message=t.error_message,
            created_at=t.created_at,
            started_at=t.started_at,
            completed_at=t.completed_at
        )
        for t in tasks
    ]
    
    return BatchTaskListResponse(
        tasks=task_responses,
        total=len(tasks),
        limit=limit,
        offset=offset
    )


@app.post("/batch/cancel/{task_id}", tags=["Batch Processing"])
async def cancel_batch_task(task_id: int):
    """取消任务"""
    success = batch_queue.cancel_task(task_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to cancel task (may already be completed)")
    
    return {"success": True, "message": f"Task {task_id} cancelled"}


@app.delete("/batch/clear-completed", tags=["Batch Processing"])
async def clear_completed_tasks(older_than_days: int = Query(default=7, ge=1)):
    """清理已完成的历史任务"""
    count = batch_queue.clear_completed(older_than_days=older_than_days)
    return {"success": True, "cleared_count": count, "older_than_days": older_than_days}


@app.get("/batch/metrics", tags=["Batch Processing"])
async def get_batch_metrics(hours: int = Query(default=24, ge=1, le=720)):
    """获取批量处理性能指标"""
    metrics = batch_queue.get_metrics(hours=hours)
    return {"hours": hours, "metrics": metrics}


# ==================== Tool Life Management Endpoints ====================

@app.post("/tools", tags=["Tool Management"])
async def create_tool(request: ToolCreateRequest):
    """创建新刀具"""
    try:
        tool = Tool(
            tool_number=request.tool_number,
            name=request.name,
            tool_type=request.tool_type,
            model=request.model,
            insert_material=request.insert_material,
            insert_shape=request.insert_shape,
            manufacturer=request.manufacturer,
            supplier=request.supplier,
            unit_price=request.unit_price,
            max_life_minutes=request.max_life_minutes,
            life_warning_threshold=request.life_warning_threshold
        )
        
        tool_id = tool_life_manager.add_tool(tool)
        
        return {
            "success": True,
            "tool_id": tool_id,
            "message": f"Tool {tool.tool_number} created successfully"
        }
    except Exception as e:
        logger.error(f"Error creating tool: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools", tags=["Tool Management"])
async def list_tools(
    tool_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0)
):
    """列出刀具"""
    tools = tool_life_manager.list_tools(
        tool_type=tool_type,
        status=status,
        limit=limit,
        offset=offset
    )
    
    tool_responses = [
        ToolResponse(
            id=t.id,
            tool_number=t.tool_number,
            name=t.name,
            tool_type=t.tool_type,
            model=t.model,
            insert_material=t.insert_material,
            insert_shape=t.insert_shape,
            manufacturer=t.manufacturer,
            supplier=t.supplier,
            unit_price=t.unit_price,
            max_life_minutes=t.max_life_minutes,
            used_life_minutes=t.used_life_minutes,
            remaining_life_minutes=t.remaining_life_minutes,
            life_percentage=round(t.life_percentage, 3),
            usage_count=t.usage_count,
            total_parts=t.total_parts,
            status=t.status,
            needs_replacement=t.needs_replacement,
            estimated_cost_per_part=round(t.estimated_cost_per_part, 2),
            install_date=t.install_date,
            last_maintenance_date=t.last_maintenance_date,
            created_at=t.created_at
        )
        for t in tools
    ]
    
    return ToolListResponse(
        tools=tool_responses,
        total=len(tools),
        limit=limit,
        offset=offset
    )


@app.get("/tools/{tool_id}", tags=["Tool Management"])
async def get_tool(tool_id: int):
    """获取刀具详情"""
    tool = tool_life_manager.get_tool(tool_id)
    
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool {tool_id} not found")
    
    return ToolResponse(
        id=tool.id,
        tool_number=tool.tool_number,
        name=tool.name,
        tool_type=tool.tool_type,
        model=tool.model,
        insert_material=tool.insert_material,
        insert_shape=tool.insert_shape,
        manufacturer=tool.manufacturer,
        supplier=tool.supplier,
        unit_price=tool.unit_price,
        max_life_minutes=tool.max_life_minutes,
        used_life_minutes=tool.used_life_minutes,
        remaining_life_minutes=tool.remaining_life_minutes,
        life_percentage=round(tool.life_percentage, 3),
        usage_count=tool.usage_count,
        total_parts=tool.total_parts,
        status=tool.status,
        needs_replacement=tool.needs_replacement,
        estimated_cost_per_part=round(tool.estimated_cost_per_part, 2),
        install_date=tool.install_date,
        last_maintenance_date=tool.last_maintenance_date,
        created_at=tool.created_at
    )


@app.post("/tools/{tool_id}/usage", tags=["Tool Management"])
async def record_tool_usage(tool_id: int, request: ToolUsageRecordRequest):
    """记录刀具使用"""
    try:
        tool = tool_life_manager.get_tool(tool_id)
        if not tool:
            raise HTTPException(status_code=404, detail=f"Tool {tool_id} not found")
        
        tool_life_manager.record_usage(
            tool_id=tool_id,
            program_name=request.program_name,
            operation_type=request.operation_type,
            duration_minutes=request.duration_minutes,
            parts_count=request.parts_count,
            wear_level=request.wear_level,
            notes=request.notes
        )
        
        # 更新刀具状态
        updated_tool = tool_life_manager.get_tool(tool_id)
        if updated_tool.status == ToolLifeStatus.WORN:
            return {
                "success": True,
                "message": f"Usage recorded. WARNING: Tool {updated_tool.tool_number} needs replacement!",
                "needs_replacement": True,
                "life_percentage": round(updated_tool.life_percentage, 3)
            }
        
        return {
            "success": True,
            "message": "Usage recorded successfully",
            "needs_replacement": False,
            "life_percentage": round(updated_tool.life_percentage, 3)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording tool usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools/{tool_id}/history", tags=["Tool Management"])
async def get_tool_history(tool_id: int, days: int = Query(default=30, ge=1, le=365)):
    """获取刀具使用历史"""
    tool = tool_life_manager.get_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool {tool_id} not found")
    
    records = tool_life_manager.get_usage_history(tool_id, days=days)
    
    return {
        "tool_id": tool_id,
        "tool_number": tool.tool_number,
        "days": days,
        "records": [r.to_dict() for r in records],
        "total_records": len(records)
    }


@app.get("/tools/statistics", tags=["Tool Management"])
async def get_tool_statistics():
    """获取刀具统计数据"""
    stats = tool_life_manager.get_tool_statistics()
    return ToolStatisticsResponse(**stats)


@app.get("/tools/warnings", tags=["Tool Management"])
async def get_tool_warnings():
    """获取刀具预警信息"""
    warnings = tool_life_manager.get_tools_warnings()
    return {"warnings": warnings, "total": len(warnings)}


@app.get("/tools/replacement-needed", tags=["Tool Management"])
async def get_tools_needing_replacement():
    """获取需要更换的刀具列表"""
    tools = tool_life_manager.get_tools_needing_replacement()
    
    return {
        "tools": [
            {
                "id": t.id,
                "tool_number": t.tool_number,
                "name": t.name,
                "life_percentage": round(t.life_percentage * 100, 1),
                "remaining_minutes": t.remaining_life_minutes
            }
            for t in tools
        ],
        "total": len(tools)
    }


@app.put("/tools/{tool_id}/status", tags=["Tool Management"])
async def update_tool_status(tool_id: int, status: str):
    """更新刀具状态"""
    tool = tool_life_manager.get_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool {tool_id} not found")
    
    valid_statuses = ["available", "in_use", "maintenance", "worn", "replaced", "scrapped"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    tool_life_manager.update_tool_status(tool_id, status)
    
    return {"success": True, "message": f"Tool {tool.tool_number} status updated to {status}"}


@app.delete("/tools/{tool_id}", tags=["Tool Management"])
async def delete_tool(tool_id: int):
    """删除刀具"""
    success = tool_life_manager.delete_tool(tool_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Tool {tool_id} not found")
    
    return {"success": True, "message": f"Tool {tool_id} deleted"}


@app.post("/tools/{tool_id}/maintenance", tags=["Tool Management"])
async def add_maintenance_record(
    tool_id: int,
    maintenance_type: str = Query(..., description="维护类型"),
    description: str = Query(..., description="维护描述"),
    cost: float = Query(default=0.0, description="维护成本"),
    performed_by: str = Query(None, description="执行人")
):
    """添加维护记录"""
    tool = tool_life_manager.get_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool {tool_id} not found")
    
    tool_life_manager.add_maintenance_record(
        tool_id=tool_id,
        maintenance_type=maintenance_type,
        description=description,
        cost=cost,
        performed_by=performed_by
    )
    
    return {"success": True, "message": "Maintenance record added"}


# ==================== Cost Accounting Endpoints ====================

@app.get("/cost/parameters", tags=["Cost Accounting"])
async def get_cost_parameters():
    """获取成本参数"""
    params = cost_manager.default_params
    return CostParameterResponse(
        machine_hourly_rate=params.machine_hourly_rate,
        labor_hourly_rate=params.labor_hourly_rate,
        overhead_rate=params.overhead_rate,
        material_waste_factor=params.material_waste_factor,
        default_tool_life_minutes=params.default_tool_life_minutes
    )


@app.put("/cost/parameters/{param_name}", tags=["Cost Accounting"])
async def set_cost_parameter(param_name: str, value: float, description: str = None):
    """设置成本参数"""
    valid_params = ["machine_hourly_rate", "labor_hourly_rate", "overhead_rate", 
                    "material_waste_factor", "default_tool_life_minutes"]
    
    if param_name not in valid_params:
        raise HTTPException(status_code=400, detail=f"Invalid parameter name. Must be one of: {valid_params}")
    
    cost_manager.set_parameter(param_name, value, description)
    
    return {"success": True, "message": f"Parameter {param_name} updated to {value}"}


@app.post("/cost/records", tags=["Cost Accounting"])
async def add_cost_record(request: CostRecordRequest):
    """添加成本记录"""
    record_id = cost_manager.add_cost_record(
        program_name=request.program_name,
        cost_type=request.cost_type,
        amount=request.amount,
        quantity=request.quantity,
        unit=request.unit,
        category=request.category,
        program_id=request.program_id,
        notes=request.notes
    )
    
    return {
        "success": True,
        "record_id": record_id,
        "message": "Cost record added successfully"
    }


@app.get("/cost/job/{program_id}", tags=["Cost Accounting"])
async def get_job_cost(program_id: int):
    """获取任务成本汇总"""
    summary = cost_manager.calculate_job_cost(program_id)
    
    return JobCostSummaryResponse(
        program_id=summary.program_id,
        program_name=summary.program_name,
        tool_cost=round(summary.tool_cost, 2),
        material_cost=round(summary.material_cost, 2),
        machine_time_cost=round(summary.machine_time_cost, 2),
        labor_cost=round(summary.labor_cost, 2),
        overhead_cost=round(summary.overhead_cost, 2),
        maintenance_cost=round(summary.maintenance_cost, 2),
        total_cost=round(summary.total_cost, 2),
        parts_count=summary.parts_count,
        cost_per_part=round(summary.cost_per_part, 2),
        machining_time_minutes=round(summary.machining_time_minutes, 2)
    )


@app.post("/cost/machining-job", tags=["Cost Accounting"])
async def record_machining_job(
    program_id: int = Query(...),
    program_name: str = Query(...),
    machining_time_minutes: float = Query(..., ge=0),
    parts_count: int = Query(..., ge=1),
    material_weight_kg: float = Query(default=0.0, ge=0),
    material_price_per_kg: float = Query(default=0.0, ge=0),
    tool_usage_json: str = Query(None, description="JSON 格式的刀具使用记录列表")
):
    """记录完整加工任务成本"""
    import json
    
    tool_usage_records = None
    if tool_usage_json:
        try:
            tool_usage_records = json.loads(tool_usage_json)
        except:
            raise HTTPException(status_code=400, detail="Invalid JSON for tool_usage_records")
    
    cost_manager.record_machining_job(
        program_id=program_id,
        program_name=program_name,
        machining_time_minutes=machining_time_minutes,
        parts_count=parts_count,
        material_weight_kg=material_weight_kg,
        material_price_per_kg=material_price_per_kg,
        tool_usage_records=tool_usage_records
    )
    
    # 计算并返回成本汇总
    summary = cost_manager.calculate_job_cost(program_id)
    
    return {
        "success": True,
        "message": "Machining job cost recorded",
        "summary": JobCostSummaryResponse(
            program_id=summary.program_id,
            program_name=summary.program_name,
            tool_cost=round(summary.tool_cost, 2),
            material_cost=round(summary.material_cost, 2),
            machine_time_cost=round(summary.machine_time_cost, 2),
            labor_cost=round(summary.labor_cost, 2),
            overhead_cost=round(summary.overhead_cost, 2),
            maintenance_cost=round(summary.maintenance_cost, 2),
            total_cost=round(summary.total_cost, 2),
            parts_count=summary.parts_count,
            cost_per_part=round(summary.cost_per_part, 2),
            machining_time_minutes=round(summary.machining_time_minutes, 2)
        )
    }


@app.get("/cost/statistics", tags=["Cost Accounting"])
async def get_cost_statistics(days: int = Query(default=30, ge=1, le=365)):
    """获取成本统计"""
    stats = cost_manager.get_cost_statistics(days=days)
    
    return CostStatisticsResponse(
        total_cost=stats["total_cost"],
        tool_cost=stats["tool_cost"],
        material_cost=stats["material_cost"],
        machine_time_cost=stats["machine_time_cost"],
        labor_cost=stats["labor_cost"],
        overhead_cost=stats["overhead_cost"],
        job_count=stats["job_count"],
        period_days=stats["period_days"]
    )


@app.get("/cost/trend", tags=["Cost Accounting"])
async def get_cost_trend(
    days: int = Query(default=30, ge=1, le=365),
    group_by: str = Query(default="day", regex="^(day|week|month)$")
):
    """获取成本趋势"""
    trend = cost_manager.get_cost_trend(days=days, group_by=group_by)
    return {"days": days, "group_by": group_by, "trend": trend}


@app.get("/cost/materials", tags=["Cost Accounting"])
async def list_material_prices():
    """列出材料价格"""
    materials = cost_manager.list_material_prices()
    return {"materials": materials, "total": len(materials)}


@app.put("/cost/materials/{material_name}", tags=["Cost Accounting"])
async def set_material_price(material_name: str, request: MaterialPriceRequest):
    """设置材料价格"""
    cost_manager.set_material_price(
        material_name=material_name,
        price_per_kg=request.price_per_kg,
        supplier=request.supplier
    )
    
    return {
        "success": True,
        "message": f"Material price set: {material_name} = ¥{request.price_per_kg}/kg"
    }


# Mount static files
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


@app.get("/web", tags=["Web UI"])
async def serve_web_ui():
    """Serve the web UI."""
    index_path = static_path / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    raise HTTPException(status_code=404, detail="Web UI not found")


# ==================== Error Handlers ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status": exc.status_code}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "status": 500}
    )


# ==================== Main ====================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.web.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
