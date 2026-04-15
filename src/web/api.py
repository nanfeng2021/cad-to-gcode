"""
CAD to G-code Platform - Web API

FastAPI-based REST API for CAD processing and G-code generation.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Query, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, FileResponse, Response, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
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
        
        # Step 2: Recognize machining features
        feature_result = recognize_features(geometry)
        
        # Handle both dict and object return types
        if isinstance(feature_result, dict):
            features_list = feature_result.get('features', [])
            feature_objects = []
        else:
            features_list = []
            feature_objects = feature_result.features if hasattr(feature_result, 'features') else []
        
        # Convert feature objects to dicts if needed
        if feature_objects and not features_list:
            for feat in feature_objects:
                feat_dict = {
                    "id": feat.id,
                    "type": feat.type.value,
                    "priority": feat.priority,
                    "parameters": feat.parameters,
                    "machining_area": feat.machining_area
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


@app.get("/tools", tags=["Tools"])
async def list_tools():
    """List available cutting tools."""
    tools = []
    for tool_type, data in cutting_engine.tools.items():
        for tool in data.get('types', []):
            tools.append({
                "type": tool_type,
                "name": tool.get('name', ''),
                "model": tool.get('insert_shape', ''),
                "applications": tool.get('applications', []),
                "materials": tool.get('materials', []),
            })
    return {"tools": tools, "count": len(tools)}


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
