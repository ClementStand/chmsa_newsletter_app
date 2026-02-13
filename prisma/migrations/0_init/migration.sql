-- CreateTable
CREATE TABLE "Competitor" (
    "id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "website" TEXT,
    "description" TEXT,
    "industry" TEXT,
    "region" TEXT,
    "status" TEXT NOT NULL DEFAULT 'active',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Competitor_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "CompetitorNews" (
    "id" TEXT NOT NULL,
    "competitorId" TEXT NOT NULL,
    "eventType" TEXT NOT NULL,
    "date" TIMESTAMP(3) NOT NULL,
    "title" TEXT NOT NULL,
    "summary" TEXT NOT NULL,
    "threatLevel" INTEGER NOT NULL,
    "region" TEXT,
    "details" TEXT NOT NULL,
    "sourceUrl" TEXT NOT NULL,
    "isRead" BOOLEAN NOT NULL DEFAULT false,
    "isStarred" BOOLEAN NOT NULL DEFAULT false,
    "extractedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "CompetitorNews_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "Competitor_name_key" ON "Competitor"("name");

-- CreateIndex
CREATE UNIQUE INDEX "CompetitorNews_sourceUrl_key" ON "CompetitorNews"("sourceUrl");

-- CreateIndex
CREATE INDEX "CompetitorNews_competitorId_date_idx" ON "CompetitorNews"("competitorId", "date");

-- CreateIndex
CREATE INDEX "CompetitorNews_eventType_idx" ON "CompetitorNews"("eventType");

-- CreateIndex
CREATE INDEX "CompetitorNews_threatLevel_idx" ON "CompetitorNews"("threatLevel");

-- CreateIndex
CREATE INDEX "CompetitorNews_isRead_idx" ON "CompetitorNews"("isRead");

-- AddForeignKey
ALTER TABLE "CompetitorNews" ADD CONSTRAINT "CompetitorNews_competitorId_fkey" FOREIGN KEY ("competitorId") REFERENCES "Competitor"("id") ON DELETE CASCADE ON UPDATE CASCADE;

