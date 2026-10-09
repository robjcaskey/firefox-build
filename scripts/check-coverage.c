#include <ft2build.h>
#include FT_FREETYPE_H
#include FT_OUTLINE_H
#include FT_LCD_FILTER_H
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define SIDE 192
static unsigned char actual[SIDE * SIDE * 3], expected[SIDE * SIDE * 3];
static void fail(const char *s, int error) { fprintf(stderr, "%s: %d\n", s, error); exit(1); }
static void copy_bitmap(FT_GlyphSlot g, unsigned char *dst, int lcd, int channel) {
  FT_Bitmap *b = &g->bitmap;
  if (b->pitch < 0) fail("unexpected negative pitch", b->pitch);
  int width = lcd == 1 ? b->width / 3 : b->width;
  unsigned height = lcd == 2 ? b->rows / 3 : b->rows;
  for (unsigned y=0; y<height; y++) for (int x=0; x<width; x++) {
    int xx=48+g->bitmap_left+x, yy=128-g->bitmap_top+y;
    if (xx<0 || xx>=SIDE || yy<0 || yy>=SIDE) fail("probe canvas overflow", 1);
    if (lcd == 2) { for(int c=0;c<3;c++) dst[(yy*SIDE+xx)*3+c]=b->buffer[(y*3+c)*b->pitch+x]; }
    else if (lcd == 1) memcpy(dst+(yy*SIDE+xx)*3, b->buffer+y*b->pitch+x*3, 3);
    else dst[(yy*SIDE+xx)*3+channel]=b->buffer[y*b->pitch+x];
  }
}
int main(int argc, char **argv) {
  if(argc<2 || argc>3 || (argc==3 && strcmp(argv[2],"vertical"))) return 2;
  int vertical=argc==3;
  FT_Library lib; FT_Face face; int e;
  if((e=FT_Init_FreeType(&lib))) fail("FT_Init_FreeType",e);
  if((e=FT_New_Face(lib,argv[1],0,&face))) fail("FT_New_Face",e);
  FT_Vector geometry[3]={{-21,-11},{0,21},{21,-11}};
  if((e=FT_Library_SetLcdGeometry(lib,geometry))) fail("set geometry",e);
  int sizes[]={12,16,19,24,32,48,72}; unsigned checks=0, differences=0;
  for(unsigned size=0;size<sizeof(sizes)/sizeof(*sizes);size++) {
    FT_Set_Pixel_Sizes(face,0,sizes[size]);
    for(unsigned ch=33;ch<127;ch++) {
      memset(actual,0,sizeof(actual)); memset(expected,0,sizeof(expected));
      if((e=FT_Load_Char(face,ch,FT_LOAD_NO_BITMAP|FT_LOAD_TARGET_NORMAL))) fail("load LCD",e);
      if((e=FT_Render_Glyph(face->glyph,vertical ? FT_RENDER_MODE_LCD_V : FT_RENDER_MODE_LCD))) fail("render LCD",e);
      copy_bitmap(face->glyph,actual,vertical ? 2 : 1,0);
      for(int c=0;c<3;c++) {
        if((e=FT_Load_Char(face,ch,FT_LOAD_NO_BITMAP|FT_LOAD_TARGET_NORMAL))) fail("load gray",e);
        FT_Outline_Translate(&face->glyph->outline,vertical ? -geometry[c].y : -geometry[c].x,vertical ? geometry[c].x : -geometry[c].y);
        if((e=FT_Render_Glyph(face->glyph,FT_RENDER_MODE_NORMAL))) fail("render gray",e);
        copy_bitmap(face->glyph,expected,0,c);
      }
      for(unsigned i=0;i<sizeof(actual);i++) if(actual[i]!=expected[i]) differences++;
      checks++;
    }
  }
  FT_Done_Face(face); FT_Done_FreeType(lib);
  printf("%u glyph/size cases, %u coverage-byte differences against three independently shifted grayscale rasters\n", checks,differences);
  return differences ? 1 : 0;
}
