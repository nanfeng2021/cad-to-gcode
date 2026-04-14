"""
CAD to G-code Platform - Web API

FastAPI-based REST API for CAD processing and G-code generation.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
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


@app.post("/gcode/upload-cad", response_model=GCodeGenerationResponse, tags=["G-code"])
async def upload_cad_and_generate(
    file: UploadFile = File(..., description="CAD file (.step, .igs, .dxf, .dwg)"),
    material: str = Form(default="45#钢", description="Material type"),
    machine_system: str = Form(default="FANUC", description="CNC control system"),
):
    """Upload a CAD file and generate G-code."""
    # Validate file extension
    allowed_extensions = [".step", ".stp", ".igs", ".ige", ".dxf", ".dwg"]
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Allowed: {allowed_extensions}"
        )
    
    # Save uploaded file temporarily
    temp_dir = Path("/tmp/cad2gcode")
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_file = temp_dir / f"{uuid.uuid4()}{file_ext}"
    
    try:
        content = await file.read()
        temp_file.write_bytes(content)
        
        logger.info(f"Saved uploaded file to: {temp_file}")
        
        # TODO: Implement CAD file parsing and feature recognition
        # For now, return a sample program
        gcode = generate_simple_shaft(
            start_diameter=50.0,
            end_diameter=30.0,
            length=100.0,
            material=material,
            machine_system=machine_system
        )
        
        lines = gcode.split("\n")
        
        return GCodeGenerationResponse(
            success=True,
            program_name=f"O{uuid.uuid4().hex[:4].upper()}",
            gcode=gcode,
            lines=len(lines),
            generated_at=datetime.now().isoformat()
        )
    
    finally:
        # Cleanup
        if temp_file.exists():
            temp_file.unlink()


@app.get("/programs", response_model=List[ProgramSummary], tags=["Programs"])
async def list_programs(limit: int = 50, offset: int = 0):
    """List all saved G-code programs with pagination."""
    try:
        programs = gcode_db.list_programs(limit=limit, offset=offset)
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


@app.post("/programs", response_model=SaveProgramResponse, tags=["Programs"])
async def save_program(request: SaveProgramRequest):
    """Save a G-code program to the database."""
    try:
        saved_id = gcode_db.save_program(
            filename=request.filename,
            content=request.content,
            material=request.material,
            operations=request.operations or [],
            metadata=request.metadata
        )
        
        logger.info(f"Saved G-code program ID: {saved_id}, filename: {request.filename}")
        
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
